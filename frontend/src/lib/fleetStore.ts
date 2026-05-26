import { create } from "zustand";

export type FleetSortKey = "rul" | "id" | "degradation";

interface FleetTableState {
  query: string;
  sortKey: FleetSortKey;
  scrollY: number;
  setQuery: (q: string) => void;
  setSortKey: (k: FleetSortKey) => void;
  setScrollY: (y: number) => void;
}

export const useFleetStore = create<FleetTableState>((set) => ({
  query: "",
  sortKey: "rul",
  scrollY: 0,
  setQuery: (query) => set({ query }),
  setSortKey: (sortKey) => set({ sortKey }),
  setScrollY: (scrollY) => set({ scrollY }),
}));
