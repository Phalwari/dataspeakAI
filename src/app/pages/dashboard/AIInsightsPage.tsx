import {
  Lightbulb,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  Target,
  ArrowRight,
  Sparkles,
  BarChart3,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { LineChart, Line, ResponsiveContainer } from "recharts";

const insights = [
  {
    id: 1,
    title: "Sales Decreased 12% This Week",
    description:
      "Revenue has dropped from $45,200 to $39,800 compared to last week. Primary decline in Enterprise segment.",
    type: "warning",
    confidence: 94,
    icon: TrendingDown,
    trend: "down",
    sparkline: [
      { value: 45 },
      { value: 44 },
      { value: 43 },
      { value: 41 },
      { value: 40 },
      { value: 39 },
    ],
    category: "Revenue",
  },
  {
    id: 2,
    title: "Customer Churn Rising in Region X",
    description:
      "15% increase in customer cancellations in the West Coast region. Recommend targeted retention campaign.",
    type: "alert",
    confidence: 88,
    icon: AlertTriangle,
    trend: "down",
    sparkline: [
      { value: 10 },
      { value: 12 },
      { value: 13 },
      { value: 14 },
      { value: 15 },
      { value: 17 },
    ],
    category: "Customer Success",
  },
  {
    id: 3,
    title: "Inventory May Run Out in 5 Days",
    description:
      "Product SKU-4567 stock level critical. Current rate: 120 units/day, remaining: 580 units.",
    type: "critical",
    confidence: 96,
    icon: AlertTriangle,
    trend: "down",
    sparkline: [
      { value: 100 },
      { value: 90 },
      { value: 75 },
      { value: 60 },
      { value: 45 },
      { value: 30 },
    ],
    category: "Inventory",
  },
  {
    id: 4,
    title: "Product A Demand Increasing Rapidly",
    description:
      "43% surge in orders for Product A over the past 2 weeks. Consider increasing production capacity.",
    type: "success",
    confidence: 91,
    icon: TrendingUp,
    trend: "up",
    sparkline: [
      { value: 30 },
      { value: 35 },
      { value: 42 },
      { value: 48 },
      { value: 55 },
      { value: 63 },
    ],
    category: "Sales",
  },
  {
    id: 5,
    title: "New Market Opportunity Detected",
    description:
      "Unusual spike in organic traffic from Brazil. Potential untapped market with high conversion rate.",
    type: "opportunity",
    confidence: 85,
    icon: Target,
    trend: "up",
    sparkline: [
      { value: 5 },
      { value: 8 },
      { value: 12 },
      { value: 18 },
      { value: 25 },
      { value: 34 },
    ],
    category: "Marketing",
  },
  {
    id: 6,
    title: "Customer Support Response Time Improving",
    description:
      "Average response time decreased from 4.2 hours to 2.1 hours. Team efficiency up 48%.",
    type: "success",
    confidence: 92,
    icon: TrendingUp,
    trend: "up",
    sparkline: [
      { value: 4.2 },
      { value: 3.8 },
      { value: 3.2 },
      { value: 2.8 },
      { value: 2.4 },
      { value: 2.1 },
    ],
    category: "Support",
  },
];

export function AIInsightsPage() {
  const getTypeStyles = (type: string) => {
    const styles = {
      warning: {
        bg: "bg-yellow-50",
        border: "border-yellow-200",
        badge: "bg-yellow-100 text-yellow-800" as const,
        icon: "text-yellow-600",
      },
      alert: {
        bg: "bg-orange-50",
        border: "border-orange-200",
        badge: "bg-orange-100 text-orange-800" as const,
        icon: "text-orange-600",
      },
      critical: {
        bg: "bg-red-50",
        border: "border-red-200",
        badge: "bg-red-100 text-red-800" as const,
        icon: "text-red-600",
      },
      success: {
        bg: "bg-green-50",
        border: "border-green-200",
        badge: "bg-green-100 text-green-800" as const,
        icon: "text-green-600",
      },
      opportunity: {
        bg: "bg-blue-50",
        border: "border-blue-200",
        badge: "bg-blue-100 text-blue-800" as const,
        icon: "text-blue-600",
      },
    };
    return styles[type as keyof typeof styles] || styles.warning;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">AI Business Recommendations</h1>
          <p className="text-gray-600 mt-1">
            Intelligent insights powered by machine learning analysis
          </p>
        </div>
        <Button className="gap-2">
          <Sparkles className="w-4 h-4" />
          Generate New Insights
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Total Insights</p>
                <p className="text-2xl font-bold">24</p>
              </div>
              <div className="w-12 h-12 rounded-lg bg-purple-100 flex items-center justify-center">
                <Lightbulb className="w-6 h-6 text-purple-600" />
              </div>
            </div>
            <p className="text-xs text-gray-600 mt-2">Updated 5 min ago</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Critical</p>
                <p className="text-2xl font-bold text-red-600">3</p>
              </div>
              <div className="w-12 h-12 rounded-lg bg-red-100 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
            </div>
            <p className="text-xs text-gray-600 mt-2">Requires action</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Opportunities</p>
                <p className="text-2xl font-bold text-green-600">8</p>
              </div>
              <div className="w-12 h-12 rounded-lg bg-green-100 flex items-center justify-center">
                <Target className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <p className="text-xs text-gray-600 mt-2">Growth potential</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Avg Confidence</p>
                <p className="text-2xl font-bold">91%</p>
              </div>
              <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center">
                <BarChart3 className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <p className="text-xs text-gray-600 mt-2">AI accuracy</p>
          </CardContent>
        </Card>
      </div>

      {/* Insights Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        {insights.map((insight) => {
          const styles = getTypeStyles(insight.type);
          const Icon = insight.icon;

          return (
            <Card
              key={insight.id}
              className={`${styles.bg} ${styles.border} border transition-all hover:shadow-lg`}
            >
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    <div
                      className={`w-10 h-10 rounded-lg bg-white flex items-center justify-center flex-shrink-0`}
                    >
                      <Icon className={`w-5 h-5 ${styles.icon}`} />
                    </div>
                    <div className="flex-1">
                      <CardTitle className="text-lg mb-2">{insight.title}</CardTitle>
                      <Badge className={styles.badge}>{insight.category}</Badge>
                    </div>
                  </div>
                  <div className="w-24 h-12">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={insight.sparkline}>
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke={
                            insight.trend === "up" ? "#10b981" : "#ef4444"
                          }
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-700 mb-4">{insight.description}</p>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="text-xs text-gray-600">Confidence Score</div>
                    <Badge variant="outline" className="text-xs">
                      {insight.confidence}%
                    </Badge>
                  </div>
                  <Button variant="ghost" size="sm" className="gap-2">
                    View Details
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
