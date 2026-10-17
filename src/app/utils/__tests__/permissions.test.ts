import { describe, it, expect } from "vitest";
import {
  canAccessPlatformAdmin,
  canModifyConversation,
  getConversationAccessBadge,
  formatRoleName,
} from "../permissions";

describe("Permissions and Access Boundary Utilities", () => {
  describe("canAccessPlatformAdmin", () => {
    it("returns false for null/undefined user", () => {
      expect(canAccessPlatformAdmin(null)).toBe(false);
      expect(canAccessPlatformAdmin(undefined)).toBe(false);
    });

    it("returns false for tenant Admin without is_platform_admin", () => {
      expect(canAccessPlatformAdmin({ role: "Admin", is_platform_admin: false })).toBe(false);
      expect(canAccessPlatformAdmin({ role: "Admin" })).toBe(false);
    });

    it("returns false for regular roles", () => {
      expect(canAccessPlatformAdmin({ role: "Developer", is_platform_admin: false })).toBe(false);
      expect(canAccessPlatformAdmin({ role: "Viewer", is_platform_admin: false })).toBe(false);
    });

    it("returns true only when is_platform_admin is true", () => {
      expect(canAccessPlatformAdmin({ role: "Admin", is_platform_admin: true })).toBe(true);
      expect(canAccessPlatformAdmin({ role: "Member", is_platform_admin: true })).toBe(true);
    });
  });

  describe("canModifyConversation", () => {
    it("returns false for null/undefined conversation", () => {
      expect(canModifyConversation(null)).toBe(false);
      expect(canModifyConversation(undefined)).toBe(false);
    });

    it("returns true for owner private conversations", () => {
      expect(canModifyConversation({ is_owner: true, is_shared: false })).toBe(true);
      expect(canModifyConversation({ is_owner: true })).toBe(true);
    });

    it("returns false for shared read-only conversations", () => {
      expect(canModifyConversation({ is_owner: false, is_shared: true })).toBe(false);
    });

    it("returns true for shared conversation if caller is creator/owner", () => {
      expect(canModifyConversation({ is_owner: true, is_shared: true })).toBe(true);
    });
  });

  describe("getConversationAccessBadge", () => {
    it("identifies read-only shared conversations", () => {
      const badge = getConversationAccessBadge({ is_owner: false, is_shared: true });
      expect(badge.isReadOnly).toBe(true);
      expect(badge.isShared).toBe(true);
      expect(badge.isOwner).toBe(false);
      expect(badge.label).toBe("Shared (Read-Only)");
    });

    it("identifies owned shared conversations", () => {
      const badge = getConversationAccessBadge({ is_owner: true, is_shared: true });
      expect(badge.isReadOnly).toBe(false);
      expect(badge.isShared).toBe(true);
      expect(badge.isOwner).toBe(true);
      expect(badge.label).toBe("Shared by you");
    });

    it("identifies owned private conversations", () => {
      const badge = getConversationAccessBadge({ is_owner: true, is_shared: false });
      expect(badge.isReadOnly).toBe(false);
      expect(badge.isShared).toBe(false);
      expect(badge.isOwner).toBe(true);
      expect(badge.label).toBeNull();
    });
  });

  describe("formatRoleName", () => {
    it("formats role names nicely", () => {
      expect(formatRoleName("admin")).toBe("Tenant Admin");
      expect(formatRoleName("Admin")).toBe("Tenant Admin");
      expect(formatRoleName("developer")).toBe("Developer");
      expect(formatRoleName("business_analyst")).toBe("Business Analyst");
      expect(formatRoleName("viewer")).toBe("Viewer");
      expect(formatRoleName(undefined)).toBe("Member");
    });
  });
});
