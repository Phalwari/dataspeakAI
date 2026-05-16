import { Link, useNavigate } from "react-router";
import { useEffect, useState } from "react";
import { API_BASE_URL } from "../config/api";
import {
  MessageSquare,
  Database,
  Shield,
  Code2,
  ArrowRight,
  Check,
  Sparkles,
  Zap,
  Lock,
  Github,
  Twitter,
  Linkedin,
  FileText,
  BarChart3,
  Brain,
  Building2,
  MessageSquareCode,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";

const features = [
  {
    icon: Brain,
    title: "AI Intelligence",
    description:
      "Advanced AI that generates insights, reports, and answers from your structured and unstructured data",
  },
  {
    icon: Database,
    title: "Multi-Database Support",
    description:
      "Connect MySQL, PostgreSQL, MongoDB, Firebase and more. Seamless integration with all major databases",
  },
  {
    icon: FileText,
    title: "RAG Document Search",
    description:
      "Upload documents for AI-powered semantic search. Query PDFs, DOCX, and more using natural language",
  },
  {
    icon: Shield,
    title: "Secure Infrastructure",
    description:
      "Enterprise-grade security with encrypted connections, role-based access, and SOC 2 compliance",
  },
  {
    icon: BarChart3,
    title: "Analytics & Visualization",
    description:
      "Beautiful dashboards and charts to visualize your data. Track trends and monitor KPIs in real-time",
  },
  {
    icon: Code2,
    title: "Easy Integration",
    description:
      "RESTful APIs and embeddable widgets. Integrate AI capabilities into your apps in minutes",
  },
];

const steps = [
  {
    number: "01",
    title: "Connect Your Data Sources",
    description:
      "Securely connect databases and upload documents. Our AI automatically indexes and prepares your data",
  },
  {
    number: "02",
    title: "AI Processes & Learns",
    description:
      "Machine learning models analyze patterns, relationships, and generate embeddings for semantic search",
  },
  {
    number: "03",
    title: "Get Insights & Deploy",
    description:
      "Receive AI-powered recommendations, deploy chatbots, and access your data through natural language",
  },
  {
    number: "04",
    title: "Monitor & Optimize",
    description:
      "Track usage analytics, monitor performance, and continuously improve with AI-driven suggestions",
  },
];

const pricingPlans = [
  {
    name: "Free",
    price: "$0",
    period: "/month",
    description: "Perfect for testing and small projects",
    features: [
      "1,000 AI queries/month",
      "1 database connection",
      "100 MB document storage",
      "Basic analytics",
      "Community support",
      "7-day logs retention",
    ],
    cta: "Get Started",
    highlighted: false,
  },
  {
    name: "Starter",
    price: "$49",
    period: "/month",
    description: "Great for growing businesses",
    features: [
      "25,000 AI queries/month",
      "5 database connections",
      "5 GB document storage",
      "Advanced analytics",
      "Email support",
      "30-day logs retention",
      "Custom branding",
      "API access",
    ],
    cta: "Start Free Trial",
    highlighted: true,
  },
  {
    name: "Pro",
    price: "$199",
    period: "/month",
    description: "For data-driven enterprises",
    features: [
      "Unlimited AI queries",
      "Unlimited databases",
      "50 GB document storage",
      "Real-time analytics",
      "Priority support",
      "Unlimited logs",
      "White-label solution",
      "Dedicated account manager",
      "Custom AI models",
    ],
    cta: "Contact Sales",
    highlighted: false,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For large-scale operations",
    features: [
      "Everything in Pro",
      "On-premise deployment",
      "SSO & SAML",
      "Dedicated infrastructure",
      "SLA guarantees",
      "Custom integrations",
      "Advanced security",
      "24/7 phone support",
    ],
    cta: "Contact Sales",
    highlighted: false,
  },
];

export function LandingPage() {
  const navigate = useNavigate();
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get("code");
    
    if (code) {
      const exchangeCode = async () => {
        setIsLoggingIn(true);
        try {
          const response = await fetch(`${API_BASE_URL}/api/auth/github-login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code }),
          });

          if (response.ok) {
            const data = await response.json();
            localStorage.setItem("token", data.access_token);
            window.history.replaceState({}, document.title, window.location.pathname);
            navigate("/dashboard");
          }
        } catch (err) {
          console.error("GitHub Login failed", err);
          setIsLoggingIn(false);
        }
      };
      exchangeCode();
    }
  }, [navigate]);

  return (
    <div className="min-h-screen bg-white">
      {isLoggingIn && (
        <div className="fixed inset-0 bg-white/80 z-50 flex items-center justify-center backdrop-blur-sm">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-lg font-semibold text-gray-800">Completing Secure Login...</p>
          </div>
        </div>
      )}
      {/* Navigation */}
      <nav className="border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <MessageSquareCode className="w-5 h-5 text-white" />
              </div>
              <span className="font-semibold text-xl">DataSpeakAI</span>
            </div>

            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm text-gray-600 hover:text-gray-900">
                Features
              </a>
              <a href="#how-it-works" className="text-sm text-gray-600 hover:text-gray-900">
                How it Works
              </a>
              <a href="#pricing" className="text-sm text-gray-600 hover:text-gray-900">
                Pricing
              </a>
              <Link to="/login">
                <Button variant="ghost">Login</Button>
              </Link>
              <Link to="/signup">
                <Button>Get Started</Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-600 px-4 py-2 rounded-full text-sm mb-6">
              <Sparkles className="w-4 h-4" />
              <span>AI-Powered Business Intelligence Platform</span>
            </div>

            <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-gray-900 via-blue-800 to-purple-800 bg-clip-text text-transparent">
              Transform Your Business Data Into Actionable Intelligence
            </h1>

            <p className="text-xl text-gray-600 mb-10">
              Connect databases, upload documents, and let AI generate insights, reports, and answers instantly. 
              Empower your team with intelligent data analysis and natural language querying.
            </p>

            <div className="flex items-center justify-center gap-4">
              <Link to="/signup">
                <Button size="lg" className="gap-2">
                  Get Started
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
              <Link to="/login">
                <Button size="lg" variant="outline">
                  Login
                </Button>
              </Link>
            </div>

            <div className="mt-12 rounded-2xl overflow-hidden shadow-2xl border border-gray-200">
              <div className="bg-gradient-to-br from-blue-50 to-purple-50 p-8">
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-3 h-3 rounded-full bg-red-400" />
                    <div className="w-3 h-3 rounded-full bg-yellow-400" />
                    <div className="w-3 h-3 rounded-full bg-green-400" />
                  </div>
                  <div className="space-y-4">
                    <div className="flex gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex-shrink-0" />
                      <div className="flex-1 bg-gray-100 rounded-lg p-3">
                        <p className="text-sm text-gray-700">
                          Show me all orders from the last 30 days
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-3 justify-end">
                      <div className="flex-1 max-w-md bg-blue-500 text-white rounded-lg p-3">
                        <p className="text-sm">
                          Found 247 orders. Total revenue: $34,567. Top product:
                          Premium Plan (89 orders)
                        </p>
                      </div>
                      <div className="w-8 h-8 rounded-full bg-gray-200 flex-shrink-0" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-6 bg-gray-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Everything you need to get started
            </h2>
            <p className="text-lg text-gray-600">
              Powerful features to transform your database into an intelligent
              assistant
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature) => (
              <Card key={feature.title} className="border-gray-200">
                <CardContent className="p-6">
                  <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-white" />
                  </div>
                  <h3 className="font-semibold mb-2">{feature.title}</h3>
                  <p className="text-sm text-gray-600">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              How It Works
            </h2>
            <p className="text-lg text-gray-600">
              Get your AI chatbot up and running in three simple steps
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {steps.map((step, index) => (
              <div key={step.number} className="relative">
                <div className="flex flex-col items-center text-center">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold mb-4">
                    {step.number}
                  </div>
                  <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                  <p className="text-gray-600">{step.description}</p>
                </div>
                {index < steps.length - 1 && (
                  <div className="hidden md:block absolute top-8 left-1/2 w-full h-0.5 bg-gradient-to-r from-blue-200 to-purple-200" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 px-6 bg-gray-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Simple, transparent pricing
            </h2>
            <p className="text-lg text-gray-600">
              Choose the plan that's right for your business
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {pricingPlans.map((plan) => (
              <Card
                key={plan.name}
                className={`relative ${
                  plan.highlighted
                    ? "border-blue-500 shadow-xl"
                    : "border-gray-200"
                }`}
              >
                {plan.highlighted && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-4 py-1 rounded-full text-sm font-medium">
                      Most Popular
                    </div>
                  </div>
                )}
                <CardContent className="p-8">
                  <h3 className="text-xl font-semibold mb-2">{plan.name}</h3>
                  <p className="text-sm text-gray-600 mb-6">
                    {plan.description}
                  </p>
                  <div className="mb-6">
                    <span className="text-4xl font-bold">{plan.price}</span>
                    <span className="text-gray-600">{plan.period}</span>
                  </div>
                  <Button
                    className={`w-full mb-6 ${
                      plan.highlighted
                        ? ""
                        : "bg-gray-900 hover:bg-gray-800"
                    }`}
                  >
                    {plan.cta}
                  </Button>
                  <ul className="space-y-3">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-3">
                        <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                        <span className="text-sm text-gray-600">{feature}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <Card className="bg-gradient-to-br from-blue-500 to-purple-600 border-0">
            <CardContent className="p-12 text-center text-white">
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                Ready to get started?
              </h2>
              <p className="text-lg text-blue-100 mb-8">
                Join thousands of businesses using DataSpeakAI to transform
                their data into actionable intelligence
              </p>
              <div className="flex items-center justify-center gap-4">
                <Link to="/signup">
                  <Button
                    size="lg"
                    variant="secondary"
                    className="gap-2"
                  >
                    Start Free Trial
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
                <Button
                  size="lg"
                  variant="outline"
                  className="bg-transparent border-white text-white hover:bg-white/10"
                >
                  Schedule Demo
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                  <MessageSquareCode className="w-4 h-4 text-white" />
                </div>
                <span className="font-semibold">DataSpeakAI</span>
              </div>
              <p className="text-sm text-gray-600">
                AI-powered business intelligence platform for data-driven decision making
              </p>
            </div>

            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li>
                  <a href="#features" className="hover:text-gray-900">
                    Features
                  </a>
                </li>
                <li>
                  <a href="#pricing" className="hover:text-gray-900">
                    Pricing
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-gray-900">
                    Documentation
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-gray-900">
                    API Reference
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li>
                  <a href="#" className="hover:text-gray-900">
                    About Us
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-gray-900">
                    Blog
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-gray-900">
                    Careers
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-gray-900">
                    Contact
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li>
                  <a href="#" className="hover:text-gray-900">
                    Privacy Policy
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-gray-900">
                    Terms of Service
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-gray-900">
                    Security
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-200 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-gray-600">
              © 2026 DataSpeakAI. All rights reserved.
            </p>
            <div className="flex items-center gap-4">
              <a href="#" className="text-gray-600 hover:text-gray-900">
                <Twitter className="w-5 h-5" />
              </a>
              <a href="#" className="text-gray-600 hover:text-gray-900">
                <Github className="w-5 h-5" />
              </a>
              <a href="#" className="text-gray-600 hover:text-gray-900">
                <Linkedin className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}