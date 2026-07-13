import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getSettings,
  setSettings,
  clearAllLocalData,
  DEFAULT_SETTINGS,
} from "./settings";
import { saveThread, listThreads, type ChatThread } from "./threads";
import {
  storeScratchTenant,
  getStoredScratchTenantId,
} from "./tenant";

function makeThread(id: string): ChatThread {
  return {
    id,
    tenantId: "tenant-a",
    title: "x",
    createdAt: "",
    updatedAt: "",
    messages: [],
  } as ChatThread;
}

beforeEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("getSettings", () => {
  it("returns defaults when nothing is stored", () => {
    expect(getSettings()).toEqual(DEFAULT_SETTINGS);
  });

  it("merges stored partial settings over the defaults", () => {
    window.localStorage.setItem(
      "groundedrag-settings",
      JSON.stringify({ density: "compact" }),
    );
    expect(getSettings()).toEqual({ ...DEFAULT_SETTINGS, density: "compact" });
  });

  it("returns defaults and logs instead of throwing on corrupt JSON", () => {
    window.localStorage.setItem("groundedrag-settings", "{not json");
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(getSettings()).toEqual(DEFAULT_SETTINGS);
    expect(errorSpy).toHaveBeenCalled();
  });
});

describe("setSettings", () => {
  it("persists a merged partial update and returns it", () => {
    const result = setSettings({ streaming: false });
    expect(result).toEqual({ ...DEFAULT_SETTINGS, streaming: false });
    expect(getSettings()).toEqual({ ...DEFAULT_SETTINGS, streaming: false });
  });

  it("layers multiple partial updates without losing earlier ones", () => {
    setSettings({ streaming: false });
    setSettings({ density: "compact" });
    expect(getSettings()).toEqual({
      ...DEFAULT_SETTINGS,
      streaming: false,
      density: "compact",
    });
  });
});

describe("clearAllLocalData", () => {
  it("removes settings back to defaults", () => {
    setSettings({ streaming: false });
    clearAllLocalData(null);
    expect(getSettings()).toEqual(DEFAULT_SETTINGS);
  });

  it("clears the given tenant's threads when a tenant id is provided", () => {
    saveThread("tenant-a", makeThread("a1"));
    clearAllLocalData("tenant-a");
    expect(listThreads("tenant-a")).toEqual([]);
  });

  it("leaves threads alone when tenant id is null", () => {
    saveThread("tenant-a", makeThread("a1"));
    clearAllLocalData(null);
    expect(listThreads("tenant-a")).toHaveLength(1);
  });

  it("clears the stored scratch tenant pointer", () => {
    storeScratchTenant("t_abc", "My scratch tenant");
    clearAllLocalData(null);
    expect(getStoredScratchTenantId()).toBeNull();
  });
});
