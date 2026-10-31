import { Navigate, Route, Routes } from "react-router";

import { LoginPage } from "../auth/LoginPage";
import { RequireAuth } from "../auth/RequireAuth";
import { FoundationPlaceholder } from "../pages/FoundationPlaceholder";
import { MarketPage } from "../v01/MarketPage";
import { ProductShell } from "./ProductShell";
import { DEFAULT_PRODUCT_ROUTE, LOGIN_ROUTE, PRODUCT_ROUTES } from "./routes";

export function AppRoutes() {
  return (
    <Routes>
      <Route path={LOGIN_ROUTE} element={<LoginPage />} />
      <Route element={<ProductShell />}>
        <Route index element={<Navigate to="/market" replace />} />
        {PRODUCT_ROUTES.map((route) => (
          <Route
            key={route.path}
            path={route.path}
            element={route.path === "/market" ? <MarketPage /> : <RequireAuth><FoundationPlaceholder title={route.title} ownerBatch={route.ownerBatch} /></RequireAuth>}
          />
        ))}
        <Route path="*" element={<Navigate to={DEFAULT_PRODUCT_ROUTE} replace />} />
      </Route>
    </Routes>
  );
}
