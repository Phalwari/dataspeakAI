import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router";
import { LogOut, Camera, Trash2, CheckCircle2, AlertCircle, Loader2, Pencil } from "lucide-react";
import { API_BASE_URL } from "../../config/api";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Separator } from "../../components/ui/separator";
import { Switch } from "../../components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Avatar, AvatarFallback, AvatarImage } from "../../components/ui/avatar";

export function SettingsPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // User Profile State
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [userRole, setUserRole] = useState("");
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [savedProfile, setSavedProfile] = useState({
    firstName: "",
    lastName: "",
    email: "",
    phone: ""
  });
  const [profileSaving, setProfileSaving] = useState(false);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [profileMessage, setProfileMessage] = useState<{ type: "success" | "error" | ""; text: string }>({ type: "", text: "" });

  const [tenantName, setTenantName] = useState("");
  const [website, setWebsite] = useState("");
  const [industry, setIndustry] = useState("");
  const [address, setAddress] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");
  
  const [members, setMembers] = useState<any[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("Viewer");
  const [inviteLink, setInviteLink] = useState("");
  const [inviteEmailSent, setInviteEmailSent] = useState<boolean | null>(null);
  const [isInviting, setIsInviting] = useState(false);
  
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState({ type: "", text: "" });
  
  const [databases, setDatabases] = useState<any[]>([]);
  const [selectedDatabases, setSelectedDatabases] = useState<number[]>([]);

  useEffect(() => {
    document.title = "Settings | DataSpeakAI";
    const fetchInitialData = async () => {
      const token = localStorage.getItem("token");
      if (!token) return;

      try {
        // Fetch Current User Profile
        const userRes = await fetch(`${API_BASE_URL}/api/auth/me`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        if (userRes.ok) {
          const userData = await userRes.json();
          const userEmail = userData.email || "";
          const userPhone = userData.phone || "";
          setEmail(userEmail);
          setUserRole(userData.role || "");
          setPhone(userPhone);
          setAvatarUrl(userData.avatar_url || "");
          
          let fn = "";
          let ln = "";
          const fullName = (userData.full_name || "").trim();
          if (fullName) {
            const parts = fullName.split(" ");
            fn = parts[0] || "";
            ln = parts.slice(1).join(" ") || "";
          }
          setFirstName(fn);
          setLastName(ln);

          setSavedProfile({
            firstName: fn,
            lastName: ln,
            email: userEmail,
            phone: userPhone
          });
        }

        // Fetch Tenant Info
        const response = await fetch(`${API_BASE_URL}/api/tenant/current`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setTenantName(data.name || "");
          setWebsite(data.website || "");
          setIndustry(data.industry || "");
          setAddress(data.address || "");
        }

        // Fetch Tenant Members
        const membersResponse = await fetch(`${API_BASE_URL}/api/tenant/members`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        if (membersResponse.ok) {
          const membersData = await membersResponse.json();
          setMembers(membersData);
        }

        // Fetch Databases
        const dbsResponse = await fetch(`${API_BASE_URL}/api/databases`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        if (dbsResponse.ok) {
          const dbsData = await dbsResponse.json();
          setDatabases(dbsData);
        }
      } catch (error) {
        console.error("Failed to fetch initial settings data:", error);
      }
    };
    fetchInitialData();
  }, []);

  const handleSaveProfile = async () => {
    setProfileSaving(true);
    setProfileMessage({ type: "", text: "" });
    const token = localStorage.getItem("token");
    if (!token) return;

    const fullName = `${firstName.trim()} ${lastName.trim()}`.trim();
    if (!fullName) {
      setProfileMessage({ type: "error", text: "Please enter your name." });
      setProfileSaving(false);
      return;
    }

    if (!email.trim()) {
      setProfileMessage({ type: "error", text: "Please enter a valid email address." });
      setProfileSaving(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          full_name: fullName,
          email: email.trim(),
          phone: phone.trim()
        })
      });

      if (res.ok) {
        const updated = await res.json();
        setProfileMessage({ type: "success", text: "Profile information updated successfully!" });
        setSavedProfile({
          firstName,
          lastName,
          email: updated.email || email,
          phone: updated.phone || phone
        });
        setIsEditingProfile(false); // Close edit mode so Edit button returns
        window.dispatchEvent(new Event("profileUpdated"));
      } else {
        const err = await res.json();
        setProfileMessage({ type: "error", text: err.detail || "Failed to update profile." });
      }
    } catch (err) {
      console.error("Profile update error:", err);
      setProfileMessage({ type: "error", text: "An error occurred while saving profile." });
    } finally {
      setProfileSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setFirstName(savedProfile.firstName);
    setLastName(savedProfile.lastName);
    setEmail(savedProfile.email);
    setPhone(savedProfile.phone);
    setIsEditingProfile(false);
    setProfileMessage({ type: "", text: "" });
  };

  const handleAvatarFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 5MB Limit Validation (Industry standard)
    const MAX_SIZE_MB = 5;
    const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
    if (file.size > MAX_SIZE_BYTES) {
      setProfileMessage({
        type: "error",
        text: `File size (${(file.size / (1024 * 1024)).toFixed(1)}MB) exceeds maximum ${MAX_SIZE_MB}MB limit. Please upload an image under 5MB.`
      });
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    const validTypes = ["image/jpeg", "image/png", "image/webp", "image/gif"];
    if (!validTypes.includes(file.type)) {
      setProfileMessage({
        type: "error",
        text: "Unsupported image format. Please upload JPG, PNG, WEBP, or GIF."
      });
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setAvatarUploading(true);
    setProfileMessage({ type: "", text: "" });
    const token = localStorage.getItem("token");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/upload-avatar`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        setAvatarUrl(data.avatar_url);
        setProfileMessage({ type: "success", text: "Profile picture uploaded successfully!" });
        window.dispatchEvent(new Event("profileUpdated"));
      } else {
        const err = await res.json();
        setProfileMessage({ type: "error", text: err.detail || "Failed to upload avatar." });
      }
    } catch (err) {
      console.error("Avatar upload error:", err);
      setProfileMessage({ type: "error", text: "Failed to upload profile picture." });
    } finally {
      setAvatarUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleRemoveAvatar = async () => {
    if (!confirm("Are you sure you want to remove your profile picture?")) return;
    const token = localStorage.getItem("token");
    setAvatarUploading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/avatar`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      if (res.ok) {
        setAvatarUrl("");
        setProfileMessage({ type: "success", text: "Profile picture removed successfully." });
        window.dispatchEvent(new Event("profileUpdated"));
      }
    } catch (err) {
      console.error("Avatar delete error:", err);
    } finally {
      setAvatarUploading(false);
    }
  };

  const getInitials = () => {
    if (firstName && lastName) return `${firstName[0]}${lastName[0]}`.toUpperCase();
    if (firstName) return firstName.slice(0, 2).toUpperCase();
    if (email) return email.slice(0, 2).toUpperCase();
    return "U";
  };

  const getFullAvatarSrc = (url: string) => {
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    return `${API_BASE_URL}${url}`;
  };

  const handleSaveCompany = async () => {
    setIsLoading(true);
    setMessage("");
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/tenant/current`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          website,
          industry,
          address
        })
      });

      if (response.ok) {
        setMessage("Company information updated successfully!");
      } else {
        setMessage("Failed to update company information.");
      }
    } catch (error) {
      console.error("Failed to save tenant:", error);
      setMessage("An error occurred while saving.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleInviteMember = async () => {
    if (!inviteEmail) return;
    setIsInviting(true);
    setInviteLink("");
    setInviteEmailSent(null);
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/tenant/invite`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ 
          email: inviteEmail, 
          role: inviteRole,
          database_ids: selectedDatabases
        })
      });

      if (response.ok) {
        const data = await response.json();
        setInviteLink(data.invite_link);
        setInviteEmailSent(Boolean(data.email_sent));
        setInviteEmail("");
      }
    } catch (error) {
      console.error("Failed to invite member:", error);
    } finally {
      setIsInviting(false);
    }
  };

  const handleRemoveMember = async (memberId: number) => {
    if (!confirm("Are you sure you want to remove this member?")) return;
    
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/tenant/members/${memberId}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });

      if (response.ok) {
        setMembers(members.filter(m => m.id !== memberId));
      } else {
        const errorData = await response.json();
        alert(errorData.detail || "Failed to remove member");
      }
    } catch (error) {
      console.error("Failed to remove member:", error);
      alert("An error occurred while removing the member");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordMessage({ type: "error", text: "Please fill in all fields" });
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordMessage({ type: "error", text: "New passwords do not match" });
      return;
    }

    setPasswordLoading(true);
    setPasswordMessage({ type: "", text: "" });
    const token = localStorage.getItem("token");

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword
        })
      });

      if (response.ok) {
        setPasswordMessage({ type: "success", text: "Password updated successfully!" });
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
      } else {
        const errorData = await response.json();
        setPasswordMessage({ type: "error", text: errorData.detail || "Failed to update password" });
      }
    } catch (error) {
      console.error("Password update error:", error);
      setPasswordMessage({ type: "error", text: "An unexpected error occurred" });
    } finally {
      setPasswordLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold mb-2">Settings</h1>
        <p className="text-gray-600">
          Manage your account and platform preferences
        </p>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="company">Company</TabsTrigger>
          <TabsTrigger value="team">Team</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
        </TabsList>

        {/* Profile Settings */}
        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Profile Information</CardTitle>
                  <p className="text-sm text-gray-500 mt-1">
                    Manage your personal account details and profile picture.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {userRole && (
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-100 text-blue-800 border border-blue-200">
                      {userRole}
                    </span>
                  )}
                  {!isEditingProfile && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setIsEditingProfile(true);
                        setProfileMessage({ type: "", text: "" });
                      }}
                      className="gap-1.5"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                      Edit Profile
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {profileMessage.text && (
                <div
                  className={`p-3 rounded-lg text-sm font-medium flex items-center gap-2 ${
                    profileMessage.type === "success"
                      ? "bg-green-50 text-green-700 border border-green-200"
                      : "bg-red-50 text-red-700 border border-red-200"
                  }`}
                >
                  {profileMessage.type === "success" ? (
                    <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                  )}
                  <span>{profileMessage.text}</span>
                </div>
              )}

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
                <div className="relative group">
                  <Avatar className="w-20 h-20 ring-2 ring-gray-100 shadow-sm">
                    <AvatarImage src={getFullAvatarSrc(avatarUrl)} alt={firstName || "Profile"} />
                    <AvatarFallback className="text-xl font-bold bg-gradient-to-br from-blue-600 to-indigo-700 text-white">
                      {getInitials()}
                    </AvatarFallback>
                  </Avatar>
                  {avatarUploading && (
                    <div className="absolute inset-0 bg-black/50 rounded-full flex items-center justify-center">
                      <Loader2 className="w-6 h-6 text-white animate-spin" />
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleAvatarFileSelected}
                      accept="image/png,image/jpeg,image/jpg,image/webp,image/gif"
                      className="hidden"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={avatarUploading}
                      className="gap-2"
                    >
                      <Camera className="w-4 h-4" />
                      {avatarUploading ? "Uploading..." : "Change Avatar"}
                    </Button>

                    {avatarUrl && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={handleRemoveAvatar}
                        disabled={avatarUploading}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50 gap-1.5"
                      >
                        <Trash2 className="w-4 h-4" />
                        Remove
                      </Button>
                    )}
                  </div>
                  <p className="text-xs text-gray-500">
                    JPG, PNG, WEBP or GIF. Max 5MB standard limit.
                  </p>
                </div>
              </div>

              <Separator />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name</Label>
                  <Input
                    id="firstName"
                    value={firstName}
                    disabled={!isEditingProfile}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="e.g. John"
                    className={!isEditingProfile ? "bg-gray-50 text-gray-700 cursor-default" : ""}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name</Label>
                  <Input
                    id="lastName"
                    value={lastName}
                    disabled={!isEditingProfile}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="e.g. Doe"
                    className={!isEditingProfile ? "bg-gray-50 text-gray-700 cursor-default" : ""}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  disabled={!isEditingProfile}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. user@example.com"
                  className={!isEditingProfile ? "bg-gray-50 text-gray-700 cursor-default" : ""}
                />
                <p className="text-xs text-gray-400">
                  Your primary login and account notification email address.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">Phone Number</Label>
                <Input
                  id="phone"
                  type="tel"
                  value={phone}
                  disabled={!isEditingProfile}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="e.g. +1 (555) 123-4567"
                  className={!isEditingProfile ? "bg-gray-50 text-gray-700 cursor-default" : ""}
                />
                <p className="text-xs text-gray-400">
                  Optional contact number for alerts and account recovery.
                </p>
              </div>

              {isEditingProfile ? (
                <div className="flex items-center gap-3 pt-2">
                  <Button
                    onClick={handleSaveProfile}
                    disabled={profileSaving}
                    className="gap-2"
                  >
                    {profileSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                    {profileSaving ? "Saving Changes..." : "Save Changes"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleCancelEdit}
                    disabled={profileSaving}
                  >
                    Cancel
                  </Button>
                </div>
              ) : (
                <div className="pt-2">
                  <Button
                    type="button"
                    onClick={() => {
                      setIsEditingProfile(true);
                      setProfileMessage({ type: "", text: "" });
                    }}
                    className="gap-2"
                  >
                    <Pencil className="w-4 h-4" />
                    Edit Profile
                  </Button>
                </div>
              )}

              <Separator className="my-6" />

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">Account Session</p>
                  <p className="text-sm text-gray-500">
                    Sign out of your account from this device.
                  </p>
                </div>
                <Button variant="destructive" onClick={handleLogout} className="gap-2">
                  <LogOut className="w-4 h-4" />
                  Sign Out
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Company Settings */}
        <TabsContent value="company">
          <Card>
            <CardHeader>
              <CardTitle>Company Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {message && <div className="text-sm font-medium text-green-600">{message}</div>}
              
              <div className="space-y-2">
                <Label htmlFor="companyName">Company Name</Label>
                <Input id="companyName" value={tenantName} disabled className="bg-gray-50" />
                <p className="text-xs text-gray-500">Company name cannot be changed.</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="website">Website</Label>
                <Input id="website" value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="https://acme.com" />
              </div>

              <div className="space-y-2">
                <Label htmlFor="industry">Industry</Label>
                <Input id="industry" value={industry} onChange={(e) => setIndustry(e.target.value)} placeholder="Technology" />
              </div>

              <div className="space-y-2">
                <Label htmlFor="address">Address</Label>
                <Input id="address" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="123 Main St, San Francisco, CA" />
              </div>

              <Button onClick={handleSaveCompany} disabled={isLoading}>
                {isLoading ? "Saving..." : "Save Changes"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Team Settings */}
        <TabsContent value="team">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Team Members</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {members.map((member) => (
                    <div key={member.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                      <div className="flex items-center gap-3">
                        <Avatar>
                          <AvatarFallback>{member.full_name?.charAt(0) || "U"}</AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="font-medium">{member.full_name || "Unknown User"}</p>
                          <p className="text-sm text-gray-500">{member.email}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-sm font-medium bg-gray-100 px-3 py-1 rounded-full text-gray-700">
                          {member.role}
                        </span>
                        <Button variant="ghost" size="sm" onClick={() => handleRemoveMember(member.id)}>Remove</Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Invite New Member</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-col sm:flex-row items-stretch sm:items-end gap-4">
                  <div className="space-y-2 flex-1">
                    <Label htmlFor="inviteEmail">Email Address</Label>
                    <Input 
                      id="inviteEmail" 
                      type="email" 
                      placeholder="colleague@example.com" 
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2 w-full sm:w-44">
                    <Label htmlFor="inviteRole">Role</Label>
                    <select
                      id="inviteRole"
                      value={inviteRole}
                      onChange={(e) => setInviteRole(e.target.value)}
                      className="w-full h-10 px-3 py-2 border rounded-md text-sm border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="Viewer">Viewer</option>
                      <option value="Business Owner">Business Owner</option>
                      <option value="Developer">Developer</option>
                      <option value="Admin">Admin</option>
                    </select>
                  </div>
                  <Button onClick={handleInviteMember} disabled={isInviting || !inviteEmail}>
                    {isInviting ? "Generating..." : "Generate Invite Link"}
                  </Button>
                </div>

                <div className="space-y-3">
                  <Label>Database Permissions</Label>
                  <p className="text-xs text-gray-500 mb-2">Select which databases this member can access. If none selected, they won't see any databases.</p>
                  <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto p-2 border rounded-md">
                    {databases.length === 0 && <p className="text-sm text-gray-400 italic col-span-2">No databases connected yet.</p>}
                    {databases.map((db) => (
                      <div key={db.id} className="flex items-center space-x-2">
                        <input 
                          type="checkbox" 
                          id={`db-${db.id}`} 
                          checked={selectedDatabases.includes(db.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedDatabases([...selectedDatabases, db.id]);
                            } else {
                              setSelectedDatabases(selectedDatabases.filter(id => id !== db.id));
                            }
                          }}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <label htmlFor={`db-${db.id}`} className="text-sm font-medium text-gray-700 truncate">
                          {db.name}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
                
                {inviteLink && (
                  <div className="mt-4 p-4 bg-blue-50 text-blue-800 border border-blue-200 rounded-md">
                    <p className="font-medium mb-2">
                      {inviteEmailSent
                        ? "Invitation email sent successfully. You can also share this link:"
                        : "Invitation generated, but email delivery is not configured. Share this link:"}
                    </p>
                    <code className="block p-2 bg-white rounded border border-blue-100 break-all text-sm">
                      {inviteLink}
                    </code>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Billing Settings */}
        <TabsContent value="billing">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Current Plan</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xl font-semibold mb-1">Starter Plan</h3>
                    <p className="text-gray-600">$29/month</p>
                    <p className="text-sm text-gray-500 mt-2">
                      Next billing date: March 6, 2026
                    </p>
                  </div>
                  <Button>Upgrade Plan</Button>
                </div>

                <Separator className="my-6" />

                <div className="space-y-3">
                  <h4 className="font-medium">Plan Includes:</h4>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>• 10,000 queries/month</li>
                    <li>• 5 database connections</li>
                    <li>• Customizable widget</li>
                    <li>• Email support</li>
                    <li>• 30-day query history</li>
                  </ul>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Payment Method</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded flex items-center justify-center text-white text-xs font-bold">
                      VISA
                    </div>
                    <div>
                      <p className="font-medium">•••• •••• •••• 4242</p>
                      <p className="text-sm text-gray-600">Expires 12/2027</p>
                    </div>
                  </div>
                  <Button variant="outline" size="sm">
                    Update
                  </Button>
                </div>

                <Button variant="outline" className="w-full">
                  Add Payment Method
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Billing History</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[
                    { date: "Feb 6, 2026", amount: "$29.00", status: "Paid" },
                    { date: "Jan 6, 2026", amount: "$29.00", status: "Paid" },
                    { date: "Dec 6, 2025", amount: "$29.00", status: "Paid" },
                  ].map((invoice, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
                    >
                      <div>
                        <p className="font-medium">{invoice.date}</p>
                        <p className="text-sm text-gray-600">
                          Starter Plan - Monthly
                        </p>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="font-medium">{invoice.amount}</span>
                        <span className="text-xs text-green-600 bg-green-100 px-2 py-1 rounded">
                          {invoice.status}
                        </span>
                        <Button variant="ghost" size="sm">
                          Download
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Notifications Settings */}
        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Email Notifications</p>
                  <p className="text-sm text-gray-600">
                    Receive updates about your account via email
                  </p>
                </div>
                <Switch defaultChecked />
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Query Alerts</p>
                  <p className="text-sm text-gray-600">
                    Get notified when queries fail
                  </p>
                </div>
                <Switch defaultChecked />
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Usage Alerts</p>
                  <p className="text-sm text-gray-600">
                    Alert when approaching usage limits
                  </p>
                </div>
                <Switch defaultChecked />
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Weekly Reports</p>
                  <p className="text-sm text-gray-600">
                    Receive weekly summary of your platform activity
                  </p>
                </div>
                <Switch />
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Product Updates</p>
                  <p className="text-sm text-gray-600">
                    News about new features and improvements
                  </p>
                </div>
                <Switch defaultChecked />
              </div>

              <Button>Save Preferences</Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Settings */}
        <TabsContent value="security">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Change Password</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {passwordMessage.text && (
                  <div className={`text-sm font-medium ${passwordMessage.type === "success" ? "text-green-600" : "text-red-600"}`}>
                    {passwordMessage.text}
                  </div>
                )}
                
                <div className="space-y-2">
                  <Label htmlFor="currentPassword">Current Password</Label>
                  <Input 
                    id="currentPassword" 
                    type="password" 
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="newPassword">New Password</Label>
                  <Input 
                    id="newPassword" 
                    type="password" 
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm New Password</Label>
                  <Input 
                    id="confirmPassword" 
                    type="password" 
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                </div>

                <Button onClick={handleChangePassword} disabled={passwordLoading}>
                  {passwordLoading ? "Updating..." : "Update Password"}
                </Button>
              </CardContent>
            </Card>

          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
