import "./styles.css";
import ApiWakeup from "./api-wakeup";
import Nav from "./nav";

const description =
  "Browse every top-five-league squad, find similar players and upgrades, and compare them side by side. Every number shows where it came from.";

export const metadata = {
  metadataBase: new URL("https://footballintelligencesystem.vercel.app"),
  title: "Football Intelligence",
  description,
  openGraph: {
    title: "Football Intelligence",
    description,
    url: "/",
    siteName: "Football Intelligence",
    type: "website",
  },
  twitter: { card: "summary_large_image", title: "Football Intelligence", description },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <ApiWakeup />
        <Nav />
        {children}
      </body>
    </html>
  );
}
