import type { Metadata } from 'next';
import './styles.css';

export const metadata: Metadata = { title: 'Smart Academic Planning', description: 'Academic planning scaffold' };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
