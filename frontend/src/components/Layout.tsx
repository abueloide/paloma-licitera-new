import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BarChart3, Database, Home } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  const navigation = [
    { name: 'Dashboard', href: '/', icon: Home },
    { name: 'Licitaciones', href: '/licitaciones', icon: Database },
    { name: 'Análisis', href: '/analytics', icon: BarChart3 },
  ];

  const isActive = (href: string) => {
    if (href === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(href);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="container">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center">
              <img 
                src="/paloma.svg" 
                alt="Paloma Licitera" 
                className="h-8 w-8 mr-3"
              />
              <h1 className="text-xl font-bold text-gray-900">
                Paloma Licitera
              </h1>
            </div>
            
            <nav className="flex space-x-4">
              {navigation.map((item) => {
                const IconComponent = item.icon;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition ${
                      isActive(item.href)
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    <IconComponent className="h-4 w-4 mr-2" />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="py-6">
        <div className="container">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t">
        <div className="container">
          <div className="py-4 text-center text-sm text-gray-600">
            <p>
              Paloma Licitera - Sistema de Monitoreo de Licitaciones Gubernamentales
            </p>
            <p className="mt-1">
              Versión 2.0.0 - {new Date().getFullYear()}
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;