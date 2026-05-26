import { useCallback, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Dropzone } from "../components/upload/Dropzone";
import { QualityReportCard } from "../components/upload/QualityReportCard";
import { SensorMappingTable } from "../components/upload/SensorMappingTable";
import { AssetMetadataForm } from "../components/upload/AssetMetadataForm";
import { MappingSummaryCard } from "../components/upload/MappingSummaryCard";
import { ProcessingStatus } from "../components/upload/ProcessingStatus";
import { StepIndicator } from "../components/upload/StepIndicator";
import { api } from "../lib/api";
import { useDataset } from "../lib/datasetContext";
import { mockProcessResult, mockUploadPreview } from "../lib/mock";
import type {
  AssetType,
  ColumnRole,
  Industry,
  SensorMapping,
  SensorSchemaPayload,
  UploadPreview,
} from "../lib/types";

type WizardStep = 1 | 2 | 3;
type ProcessState = "idle" | "running" | "success" | "error";

function buildInitialMappings(preview: UploadPreview): SensorMapping[] {
  return preview.columns.map((col) => {
    const role = (preview.suggestions[col] ?? "sensor") as ColumnRole;
    return {
      column_name: col,
      role,
      display_name: role === "sensor" ? col : "",
      type_tag: "custom",
      unit: "",
      warning_threshold: null,
      critical_threshold: null,
    };
  });
}

function findColumnByRole(mappings: SensorMapping[], role: ColumnRole): string {
  return mappings.find((m) => m.role === role)?.column_name ?? "";
}

function buildSchemaPayload(
  preview: UploadPreview,
  mappings: SensorMapping[],
  assetId: string,
  industry: Industry,
  assetType: AssetType,
): SensorSchemaPayload {
  return {
    upload_id: preview.upload_id,
    asset_id: assetId.trim(),
    asset_type: assetType,
    industry,
    cycle_column: findColumnByRole(mappings, "cycle"),
    unit_id_column: findColumnByRole(mappings, "unit_id"),
    rul_column: findColumnByRole(mappings, "rul") || null,
    mappings: mappings.filter((m) => m.role !== "ignore"),
    tenant_id: "default",
  };
}

function validateStepTwo(
  mappings: SensorMapping[],
  assetId: string,
): string | null {
  const unitCols = mappings.filter((m) => m.role === "unit_id").length;
  const cycleCols = mappings.filter((m) => m.role === "cycle").length;
  const sensorCols = mappings.filter((m) => m.role === "sensor").length;
  if (!assetId.trim()) return "Asset ID is required.";
  if (unitCols !== 1) return "Map exactly one column as unit_id.";
  if (cycleCols !== 1) return "Map exactly one column as cycle.";
  if (sensorCols < 3) return `At least 3 sensor columns required (got ${sensorCols}).`;
  return null;
}

export function Upload() {
  const { refresh: refreshDatasets, setActiveDatasetId } = useDataset();
  const [step, setStep] = useState<WizardStep>(1);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<UploadPreview | null>(null);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [mappings, setMappings] = useState<SensorMapping[]>([]);
  const [assetId, setAssetId] = useState("");
  const [industry, setIndustry] = useState<Industry>("oil_gas");
  const [assetType, setAssetType] = useState<AssetType>("centrifugal_compressor");
  const [stepTwoError, setStepTwoError] = useState<string | null>(null);

  const [processState, setProcessState] = useState<ProcessState>("idle");
  const [processMessage, setProcessMessage] = useState<string | undefined>();
  const [processErrors, setProcessErrors] = useState<string[]>([]);
  const [processedDatasetId, setProcessedDatasetId] = useState<string | undefined>();

  const handleFile = useCallback(async (chosen: File) => {
    setFile(chosen);
    setUploadBusy(true);
    setUploadError(null);
    try {
      const result = await api.uploadFile(chosen);
      setPreview(result);
      setMappings(buildInitialMappings(result));
      const suggested = chosen.name.replace(/\.[^.]+$/, "");
      setAssetId((prev) => prev || suggested);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed.";
      setUploadError(`${message} — using built-in CMAPSS sample instead.`);
      setPreview(mockUploadPreview);
      setMappings(buildInitialMappings(mockUploadPreview));
      setAssetId((prev) => prev || "demo-compressor");
    } finally {
      setUploadBusy(false);
    }
  }, []);

  const handleMappingChange = useCallback(
    (index: number, patch: Partial<SensorMapping>) => {
      setMappings((prev) => {
        const next = [...prev];
        next[index] = { ...next[index], ...patch };
        return next;
      });
    },
    [],
  );

  const proceedToStepTwo = () => {
    if (!preview) return;
    setStep(2);
  };

  const proceedToStepThree = () => {
    if (!preview) return;
    const err = validateStepTwo(mappings, assetId);
    if (err) {
      setStepTwoError(err);
      return;
    }
    setStepTwoError(null);
    setStep(3);
  };

  const startProcessing = async () => {
    if (!preview) return;
    setProcessState("running");
    setProcessMessage(undefined);
    setProcessErrors([]);
    const payload = buildSchemaPayload(
      preview,
      mappings,
      assetId,
      industry,
      assetType,
    );
    try {
      const result = await api.submitSchema(payload);
      if (result.status !== "ready") {
        setProcessState("error");
        setProcessErrors(result.errors.length ? result.errors : ["Processing failed."]);
        return;
      }
      setProcessedDatasetId(result.dataset_id);
      setProcessMessage(
        `${result.meta.engine_count} engine${result.meta.engine_count === 1 ? "" : "s"} · ` +
          `${result.meta.sensor_count} sensor${result.meta.sensor_count === 1 ? "" : "s"}`,
      );
      setProcessState("success");
      // Pull the new dataset into the context and make it active so the
      // header dropdown and /fleet immediately reflect the upload.
      await refreshDatasets();
      setActiveDatasetId(result.dataset_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Processing failed.";
      setProcessState("success");
      setProcessedDatasetId(mockProcessResult.dataset_id);
      setProcessMessage(`${message} — showing mock result.`);
    }
  };

  const reset = () => {
    setStep(1);
    setFile(null);
    setPreview(null);
    setMappings([]);
    setAssetId("");
    setProcessState("idle");
    setProcessMessage(undefined);
    setProcessErrors([]);
    setProcessedDatasetId(undefined);
    setUploadError(null);
    setStepTwoError(null);
  };

  const stepTwoValidationLive = useMemo(
    () => validateStepTwo(mappings, assetId),
    [mappings, assetId],
  );

  return (
    <div className="relative z-10 flex flex-1 flex-col overflow-y-auto px-6 py-6">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-[18px] font-semibold text-text">Upload Dataset</h1>
            <p className="text-[12px] text-text-dim">
              Bring your own sensor data — any rotating machinery, any industry.
            </p>
          </div>
          <StepIndicator current={step} />
        </header>

        <AnimatePresence mode="wait">
          {step === 1 && (
            <motion.section
              key="step-1"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
              className="space-y-4"
            >
              <Dropzone
                onFile={handleFile}
                busy={uploadBusy}
                selected={file ? { name: file.name, size: file.size } : null}
              />
              {uploadError && (
                <p className="rounded-md border border-status-amber/30 bg-status-amber/5 px-3 py-2 text-[12px] text-status-amber">
                  {uploadError}
                </p>
              )}
              {preview && <QualityReportCard preview={preview} />}
              <div className="flex justify-end">
                <button
                  type="button"
                  disabled={!preview || uploadBusy}
                  onClick={proceedToStepTwo}
                  className="flex items-center gap-1.5 rounded-md border border-violet/40 bg-gradient-to-b from-violet/25 to-violet/10 px-4 py-2 text-[12px] font-medium text-white shadow-[0_0_24px_rgba(168,85,247,0.25),inset_0_1px_0_rgba(255,255,255,0.1)] enabled:hover:from-violet/35 enabled:hover:to-violet/15 disabled:opacity-50"
                >
                  Map Sensors
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </motion.section>
          )}

          {step === 2 && preview && (
            <motion.section
              key="step-2"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
              className="space-y-4"
            >
              <AssetMetadataForm
                assetId={assetId}
                industry={industry}
                assetType={assetType}
                onChange={(patch) => {
                  if (patch.assetId !== undefined) setAssetId(patch.assetId);
                  if (patch.industry) setIndustry(patch.industry);
                  if (patch.assetType) setAssetType(patch.assetType);
                }}
              />
              <SensorMappingTable
                mappings={mappings}
                onChange={handleMappingChange}
              />
              {(stepTwoError || stepTwoValidationLive) && (
                <p className="text-[12px] text-status-amber">
                  {stepTwoError ?? stepTwoValidationLive}
                </p>
              )}
              <div className="flex justify-between">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-[12px] text-text-dim hover:bg-surface-hover hover:text-text"
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Back
                </button>
                <button
                  type="button"
                  disabled={Boolean(stepTwoValidationLive)}
                  onClick={proceedToStepThree}
                  className="flex items-center gap-1.5 rounded-md border border-violet/40 bg-gradient-to-b from-violet/25 to-violet/10 px-4 py-2 text-[12px] font-medium text-white shadow-[0_0_24px_rgba(168,85,247,0.25),inset_0_1px_0_rgba(255,255,255,0.1)] enabled:hover:from-violet/35 enabled:hover:to-violet/15 disabled:opacity-50"
                >
                  Review
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </motion.section>
          )}

          {step === 3 && preview && (
            <motion.section
              key="step-3"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
              className="space-y-4"
            >
              <MappingSummaryCard
                assetId={assetId}
                industry={industry}
                assetType={assetType}
                engineCount={preview.quality.engines_loaded || "—"}
                mappings={mappings}
                hasRul={mappings.some((m) => m.role === "rul")}
              />
              {processState === "idle" ? (
                <div className="flex justify-between">
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-[12px] text-text-dim hover:bg-surface-hover hover:text-text"
                  >
                    <ArrowLeft className="h-3.5 w-3.5" />
                    Back
                  </button>
                  <button
                    type="button"
                    onClick={startProcessing}
                    className="rounded-md border border-violet/40 bg-gradient-to-b from-violet/25 to-violet/10 px-4 py-2 text-[12px] font-medium text-white shadow-[0_0_24px_rgba(168,85,247,0.25),inset_0_1px_0_rgba(255,255,255,0.1)] hover:from-violet/35 hover:to-violet/15"
                  >
                    Process Dataset
                  </button>
                </div>
              ) : (
                <ProcessingStatus
                  state={processState === "idle" ? "running" : processState}
                  message={processMessage}
                  errors={processErrors}
                  datasetId={processedDatasetId}
                  onReset={reset}
                />
              )}
            </motion.section>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
