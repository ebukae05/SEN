'use client'

import { Settings, Bell, Database, Cpu, Shield, Palette } from 'lucide-react'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Button } from '@/components/ui/button'

export function SettingsView() {
  return (
    <div className="p-6 h-full overflow-auto">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <Settings className="w-6 h-6 text-primary" />
          <h2 className="text-2xl font-bold text-foreground">Settings</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Configure SEN monitoring and notification preferences
        </p>
      </div>

      <div className="max-w-2xl space-y-6">
        {/* Notifications */}
        <div className="p-6 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-primary/10">
              <Bell className="w-5 h-5 text-primary" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">Notifications</h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">Critical Alerts</Label>
                <p className="text-xs text-muted-foreground">
                  Receive immediate notifications for critical engine status
                </p>
              </div>
              <Switch defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">Watch Alerts</Label>
                <p className="text-xs text-muted-foreground">
                  Notify when engines enter watch status
                </p>
              </div>
              <Switch defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">Daily Summary</Label>
                <p className="text-xs text-muted-foreground">
                  Receive daily fleet health digest
                </p>
              </div>
              <Switch />
            </div>
          </div>
        </div>

        {/* Thresholds */}
        <div className="p-6 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-status-watch/10">
              <Cpu className="w-5 h-5 text-status-watch" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">Alert Thresholds</h3>
          </div>
          <div className="space-y-6">
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label className="text-foreground">Critical Threshold (RUL)</Label>
                <span className="text-sm font-medium text-status-critical">50 cycles</span>
              </div>
              <Slider defaultValue={[50]} max={100} step={5} />
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label className="text-foreground">Watch Threshold (RUL)</Label>
                <span className="text-sm font-medium text-status-watch">100 cycles</span>
              </div>
              <Slider defaultValue={[100]} max={200} step={10} />
            </div>
          </div>
        </div>

        {/* Data Settings */}
        <div className="p-6 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-accent/10">
              <Database className="w-5 h-5 text-accent" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">Data & Sync</h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">Real-time Telemetry</Label>
                <p className="text-xs text-muted-foreground">
                  Stream live sensor data from engines
                </p>
              </div>
              <Switch defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">Auto-refresh Predictions</Label>
                <p className="text-xs text-muted-foreground">
                  Automatically update RUL predictions every 5 minutes
                </p>
              </div>
              <Switch defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">Historical Data Retention</Label>
                <p className="text-xs text-muted-foreground">
                  Keep sensor history for 90 days
                </p>
              </div>
              <Switch defaultChecked />
            </div>
          </div>
        </div>

        {/* Display */}
        <div className="p-6 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-status-healthy/10">
              <Palette className="w-5 h-5 text-status-healthy" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">Display</h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">Particle Effects</Label>
                <p className="text-xs text-muted-foreground">
                  Show animated background particles
                </p>
              </div>
              <Switch defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">Glow Animations</Label>
                <p className="text-xs text-muted-foreground">
                  Enable status-based glow effects
                </p>
              </div>
              <Switch defaultChecked />
            </div>
          </div>
        </div>

        {/* Security */}
        <div className="p-6 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-primary/10">
              <Shield className="w-5 h-5 text-primary" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">Security</h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">API Access</Label>
                <p className="text-xs text-muted-foreground">
                  Manage API keys and access tokens
                </p>
              </div>
              <Button variant="outline" size="sm">Manage Keys</Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">Audit Logging</Label>
                <p className="text-xs text-muted-foreground">
                  Log all system access and changes
                </p>
              </div>
              <Switch defaultChecked />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
