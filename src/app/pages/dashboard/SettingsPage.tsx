import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { LogOut } from "lucide-react";
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
    const fetchTenant = async () => {
      const token = localStorage.getItem("token");
      if (!token) return;

      try {
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

        const membersResponse = await fetch(`${API_BASE_URL}/api/tenant/members`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        if (membersResponse.ok) {
          const membersData = await membersResponse.json();
          setMembers(membersData);
        }

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
        console.error("Failed to fetch tenant or members:", error);
      }
    };
    fetchTenant();
  }, []);

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
              <CardTitle>Profile Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center gap-6">
                <Avatar className="w-20 h-20">
                  <AvatarImage src="" />
                  <AvatarFallback className="text-lg">JD</AvatarFallback>
                </Avatar>
                <div className="space-y-2">
                  <Button variant="outline" size="sm">
                    Change Avatar
                  </Button>
                  <p className="text-xs text-gray-600">
                    JPG, PNG or GIF. Max 2MB.
                  </p>
                </div>
              </div>

              <Separator />

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name</Label>
                  <Input id="firstName" defaultValue="John" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name</Label>
                  <Input id="lastName" defaultValue="Doe" />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" defaultValue="john@example.com" />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">Phone Number</Label>
                <Input id="phone" type="tel" defaultValue="+1 (555) 123-4567" />
              </div>

              <Button>Save Changes</Button>

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
                    <p className="font-medium mb-2">Invitation generated successfully! Share this link with your team member:</p>
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
