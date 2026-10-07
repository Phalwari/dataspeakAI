import { RouterProvider } from "react-router";
import { router } from "./routes";
import { Toaster } from "./components/ui/sonner";
import { AnalyticsProvider } from "./context/AnalyticsContext";

export default function App() {
  return (
    <AnalyticsProvider>
      <RouterProvider router={router} />
      <Toaster />
    </AnalyticsProvider>
  );
}
