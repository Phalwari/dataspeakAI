/**
 * src/app/utils/permissions.ts
 * ----------------------------
 * Pure utility functions for user permissions, effective role indicators,
 * and conversation access boundaries without treating hidden UI controls as security.
 */

export interface PermissionUser {
  id?: number;
  email?: string;
  role?: string;
  is_platform_admin?: boolean;
}

export interface PermissionConversation {
  id?: number;
  is_owner?: boolean;
  is_shared?: boolean;
  user_id?: number | null;
}

/**
 * Checks whether the user has explicit Platform Administrator authority.
 * Tenant "Admin" role alone is insufficient for platform governance.
 */
export function canAccessPlatformAdmin(user: PermissionUser | null | undefined): boolean {
  return Boolean(user?.is_platform_admin === true);
}

/**
 * Checks whether the user can modify (rename, delete, write messages to) a conversation.
 * Shared conversations granted to non-owners are strictly read-only.
 */
export function canModifyConversation(conv: PermissionConversation | null | undefined): boolean {
  if (!conv) return false;
  if (conv.is_shared && !conv.is_owner) {
    return false;
  }
  return conv.is_owner !== false;
}

/**
 * Derives conversation badge information for UI status reflection.
 */
export function getConversationAccessBadge(conv: PermissionConversation | null | undefined): {
  isOwner: boolean;
  isShared: boolean;
  isReadOnly: boolean;
  label: string | null;
  description: string;
} {
  if (!conv) {
    return {
      isOwner: true,
      isShared: false,
      isReadOnly: false,
      label: null,
      description: "Default conversation",
    };
  }

  const isShared = Boolean(conv.is_shared);
  const isOwner = conv.is_owner !== false;
  const isReadOnly = isShared && !isOwner;

  if (isReadOnly) {
    return {
      isOwner: false,
      isShared: true,
      isReadOnly: true,
      label: "Shared (Read-Only)",
      description: "Shared with you with read-only view privileges",
    };
  }

  if (isShared && isOwner) {
    return {
      isOwner: true,
      isShared: true,
      isReadOnly: false,
      label: "Shared by you",
      description: "Created by you and shared with other team members",
    };
  }

  return {
    isOwner: true,
    isShared: false,
    isReadOnly: false,
    label: null,
    description: "Private conversation owned by you",
  };
}

/**
 * Formats user role label for display.
 */
export function formatRoleName(role?: string): string {
  if (!role) return "Member";
  switch (role.toLowerCase()) {
    case "admin":
      return "Tenant Admin";
    case "developer":
      return "Developer";
    case "business_analyst":
    case "business analyst":
      return "Business Analyst";
    case "viewer":
      return "Viewer";
    default:
      return role.charAt(0).toUpperCase() + role.slice(1);
  }
}
