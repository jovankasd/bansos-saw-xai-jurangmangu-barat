import React, { ReactElement } from "react";
import { render, RenderOptions } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { User } from "./types/auth";

interface CustomRenderOptions extends Omit<RenderOptions, "wrapper"> {
  user?: User | null;
  route?: string;
  initialToken?: string | null;
}

export function renderWithProviders(
  ui: ReactElement,
  {
    user = { name: "Budi Hartono, S.STP", role: "SUPER_ADMIN", rt_number: null },
    route = "/",
    initialToken = "mock_access_token",
    ...renderOptions
  }: CustomRenderOptions = {}
) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter initialEntries={[route]}>
        <AuthProvider initialUser={user} initialToken={initialToken}>
          {children}
        </AuthProvider>
      </MemoryRouter>
    );
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  };
}

export * from "@testing-library/react";
