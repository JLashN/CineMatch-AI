import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'CineMatch AI — Motor de Recomendación Cinematográfica',
  description: 'Descubre películas perfectas para ti con inteligencia artificial',
  icons: { icon: '🎬' },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-cinema-bg text-cinema-text min-h-screen">
        {children}
      </body>
    </html>
  );
}
