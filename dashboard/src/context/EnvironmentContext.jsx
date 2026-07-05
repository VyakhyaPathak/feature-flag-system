import { createContext, useState, useContext } from "react";

const EnvironmentContext = createContext();

export function EnvironmentProvider({ children }) {
  const [environment, setEnvironment] = useState("development");

  return (
    <EnvironmentContext.Provider value={{ environment, setEnvironment }}>
      {children}
    </EnvironmentContext.Provider>
  );
}

export function useEnvironment() {
  return useContext(EnvironmentContext);
}