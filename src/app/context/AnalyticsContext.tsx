import React, { createContext, useContext, useState, ReactNode } from "react";

export interface AnalyticsContextType {
  selectedDatasetId: string;
  setSelectedDatasetId: (id: string) => void;
  rawData: any[];
  setRawData: (data: any[]) => void;
  mlData: any;
  setMlData: (data: any) => void;
  filename: string;
  setFilename: (name: string) => void;
  resetAnalytics: () => void;
}

const AnalyticsContext = createContext<AnalyticsContextType | undefined>(undefined);

export function AnalyticsProvider({ children }: { children: ReactNode }) {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const [rawData, setRawData] = useState<any[]>([]);
  const [mlData, setMlData] = useState<any>(null);
  const [filename, setFilename] = useState<string>("");

  const resetAnalytics = () => {
    setSelectedDatasetId("");
    setRawData([]);
    setMlData(null);
    setFilename("");
  };

  return (
    <AnalyticsContext.Provider
      value={{
        selectedDatasetId,
        setSelectedDatasetId,
        rawData,
        setRawData,
        mlData,
        setMlData,
        filename,
        setFilename,
        resetAnalytics,
      }}
    >
      {children}
    </AnalyticsContext.Provider>
  );
}

export const useAnalytics = (): AnalyticsContextType => {
  const context = useContext(AnalyticsContext);
  if (!context) {
    throw new Error("useAnalytics must be used within an AnalyticsProvider");
  }
  return context;
};
