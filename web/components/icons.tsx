// Minimal hand-rolled icon set (no external icon package) so the sidebar /
// header / dialogs have consistent, lightweight SVG glyphs.
import type { SVGProps } from "react";

function Base(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    />
  );
}

export const IconPos = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" /></Base>
);
export const IconTables = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><circle cx="12" cy="12" r="8" /><path d="M12 4v16M4 12h16" /></Base>
);
export const IconKds = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><rect x="3" y="3" width="18" height="14" rx="2" /><path d="M9 21h6M12 17v4" /></Base>
);
export const IconOrders = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><path d="M6 2h9l3 3v17H6z" /><path d="M9 9h6M9 13h6M9 17h3" /></Base>
);
export const IconSync = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><path d="M4 4v6h6M20 20v-6h-6" /><path d="M5 13a7 7 0 0 1 12.3-4.3M19 11a7 7 0 0 1-12.3 4.3" /></Base>
);
export const IconShifts = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></Base>
);
export const IconAdmin = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><path d="M4 21v-7a8 8 0 0 1 16 0v7" /><path d="M4 21h16" /></Base>
);
export const IconLogout = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="M16 17l5-5-5-5M21 12H9" /></Base>
);
export const IconWifi = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><path d="M5 12.5a11 11 0 0 1 14 0" /><path d="M8.5 16a6 6 0 0 1 7 0" /><path d="M12 19.5h.01" /></Base>
);
export const IconWifiOff = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><path d="M3 3l18 18" /><path d="M5 12.5a11 11 0 0 1 10.5-3M19 9.5a11 11 0 0 1 .6.5" /><path d="M8.5 16a6 6 0 0 1 7 0" /><path d="M12 19.5h.01" /></Base>
);
export const IconPlus = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><path d="M12 5v14M5 12h14" /></Base>
);
export const IconMinus = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><path d="M5 12h14" /></Base>
);
export const IconClose = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><path d="M6 6l12 12M18 6L6 18" /></Base>
);
export const IconPrint = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><path d="M6 9V3h12v6" /><rect x="4" y="9" width="16" height="8" rx="1" /><path d="M6 17h12v4H6z" /></Base>
);
export const IconCheck = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><path d="M5 12l5 5L20 7" /></Base>
);
export const IconSearch = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></Base>
);
export const IconBack = (p: SVGProps<SVGSVGElement>) => (
  <Base {...p}><path d="M15 18l-6-6 6-6" /></Base>
);
