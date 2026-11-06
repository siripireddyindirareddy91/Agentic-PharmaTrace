import "./globals.css";
import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "PharmaTrace AI — Supply chain intelligence",
  description:
    "Evidence-led pharmaceutical traceability and risk investigation. Synthetic demonstration.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
