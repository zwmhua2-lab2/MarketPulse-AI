import { Navigate, Route, Routes } from "react-router";

import { LoginPage } from "../auth/LoginPage";
import { RequireAuth } from "../auth/RequireAuth";
import { FoundationPlaceholder } from "../pages/FoundationPlaceholder";
import { MarketPage } from "../v01/MarketPage";
import { ProductShell } from "./ProductShell";
import { DEFAULT_PRODUCT_ROUTE, LOGIN_ROUTE, PRODUCT_ROUTES } from "./routes";

/**
 * Declarative route topology (UI-F01 §6).
 *
 * `/login` is the Auth Shell. Everything else lives inside one authenticated
 * product shell holding exactly the five frozen product routes.
 */
export function AppRoutes() {
  return (
    <Routes>
      <Route path={LOGIN_ROUTE} element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <ProductShell />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to={DEFAULT_PRODUCT_ROUTE} replace />} />
        {PRODUCT_ROUTES.map((route) => (
          <Route
            key={route.path}
            path={route.path}
            element={route.path === "/market" ? <MarketPage /> : <FoundationPlaceholder title={route.title} ownerBatch={route.ownerBatch} />}
          />
        ))}
        <Route path="*" element={<Navigate to={DEFAULT_PRODUCT_ROUTE} replace />} />
      </Route>
    </Routes>
  );
}
