import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  listThreads,
  saveThread,
  renameThread,
  deleteThread,
  clearThreads,
  type ChatThread,
} from "./threads";

function makeThread(overrides: Partial<ChatThread> = {}): ChatThread {
  return {
    id: "t1",
    tenantId: "tenant-a",
    title: "Untitled",
    createdAt: "2026-01-01T00:00:00.000Z",
    updatedAt: "2026-01-01T00:00:00.000Z",
    messages: [],
    ...overrides,
  } as ChatThread;
}

beforeEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("listThreads", () => {
  it("returns an empty array when nothing is stored", () => {
    expect(listThreads("tenant-a")).toEqual([]);
  });

  it("returns an empty array and logs instead of throwing on corrupt JSON", () => {
    window.localStorage.setItem("groundedrag-threads-tenant-a", "{not json");
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(listThreads("tenant-a")).toEqual([]);
    expect(errorSpy).toHaveBeenCalled();
  });

  it("keeps tenants isolated by storage key", () => {
    saveThread("tenant-a", makeThread({ id: "a1" }));
    saveThread("tenant-b", makeThread({ id: "b1" }));
    expect(listThreads("tenant-a").map((t) => t.id)).toEqual(["a1"]);
    expect(listThreads("tenant-b").map((t) => t.id)).toEqual(["b1"]);
  });
});

describe("saveThread", () => {
  it("prepends a new thread", () => {
    saveThread("tenant-a", makeThread({ id: "a1" }));
    saveThread("tenant-a", makeThread({ id: "a2" }));
    expect(listThreads("tenant-a").map((t) => t.id)).toEqual(["a2", "a1"]);
  });

  it("upserts an existing thread in place instead of duplicating it", () => {
    saveThread("tenant-a", makeThread({ id: "a1", title: "First" }));
    saveThread("tenant-a", makeThread({ id: "a2" }));
    saveThread("tenant-a", makeThread({ id: "a1", title: "Updated" }));
    const threads = listThreads("tenant-a");
    expect(threads).toHaveLength(2);
    expect(threads.find((t) => t.id === "a1")?.title).toBe("Updated");
  });
});

describe("renameThread", () => {
  it("renames the matching thread and leaves others untouched", () => {
    saveThread("tenant-a", makeThread({ id: "a1", title: "Old" }));
    saveThread("tenant-a", makeThread({ id: "a2", title: "Keep" }));
    renameThread("tenant-a", "a1", "New");
    const threads = listThreads("tenant-a");
    expect(threads.find((t) => t.id === "a1")?.title).toBe("New");
    expect(threads.find((t) => t.id === "a2")?.title).toBe("Keep");
  });

  it("is a no-op when the thread id does not exist", () => {
    saveThread("tenant-a", makeThread({ id: "a1", title: "Old" }));
    renameThread("tenant-a", "missing", "New");
    expect(listThreads("tenant-a")[0].title).toBe("Old");
  });
});

describe("deleteThread", () => {
  it("removes only the matching thread", () => {
    saveThread("tenant-a", makeThread({ id: "a1" }));
    saveThread("tenant-a", makeThread({ id: "a2" }));
    deleteThread("tenant-a", "a1");
    expect(listThreads("tenant-a").map((t) => t.id)).toEqual(["a2"]);
  });
});

describe("clearThreads", () => {
  it("removes all threads for the tenant", () => {
    saveThread("tenant-a", makeThread({ id: "a1" }));
    clearThreads("tenant-a");
    expect(listThreads("tenant-a")).toEqual([]);
  });

  it("does not affect other tenants", () => {
    saveThread("tenant-a", makeThread({ id: "a1" }));
    saveThread("tenant-b", makeThread({ id: "b1" }));
    clearThreads("tenant-a");
    expect(listThreads("tenant-b").map((t) => t.id)).toEqual(["b1"]);
  });
});
