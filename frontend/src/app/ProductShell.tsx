import { NavLink, Outlet } from "react-router";

import { useAuthSession } from "../auth/AuthSessionProvider";
import { PRODUCT_ROUTES } from "./routes";

/**
 * The authenticated product shell.
 *
 * Read-only by construction: the only interactive control here is signing out.
 * UI V1 ships no trading, risk, scanner or runtime control (UI-V1-D01 §3, §6.4, §30).
 */
export function ProductShell() {
  const { signOut, status } = useAuthSession();

  return (
    <div className="product-shell">
      <header className="product-shell__header">
        <p className="eyebrow">MARKETPULSE AI · V1</p>
        <nav aria-label="主导航">
          <ul className="product-shell__nav">
            {PRODUCT_ROUTES.map((route) => (
              <li key={route.path}>
                <NavLink to={route.path}>{route.title}</NavLink>
              </li>
            ))}
          </ul>
        </nav>
        {status === "authenticated" && <button type="button" onClick={signOut}>
          退出登录
        </button>}
      </header>
      <main className="product-shell__main">
        <Outlet />
      </main>
    </div>
  );
}
