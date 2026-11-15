import { Link, Navigate, Route, Routes } from 'react-router-dom';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import { useAuth } from './context/AuthContext';
import { ROLE_HOME, ROLES } from './utils/constants';

import Login from './pages/Login';
import Register from './pages/Register';
import Restaurants from './pages/Restaurants';
import RestaurantMenu from './pages/RestaurantMenu';
import Cart from './pages/Cart';
import CustomerOrders from './pages/CustomerOrders';
import AIInsights from './pages/AIInsights';
import OwnerDashboard from './pages/OwnerDashboard';
import OwnerOrders from './pages/OwnerOrders';
import MenuManagement from './pages/MenuManagement';
import DeliveryDashboard from './pages/DeliveryDashboard';

function NotFound() {
  const { user } = useAuth();
  return (
    <div className="empty">
      <h2>Page not found</h2>
      <Link className="btn" to={user ? ROLE_HOME[user.role] : '/login'}>
        Go home
      </Link>
    </div>
  );
}

export default function App() {
  const { user } = useAuth();
  return (
    <>
      <Navbar />
      <main className="container">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route element={<ProtectedRoute roles={[ROLES.CUSTOMER]} />}>
            <Route path="/" element={<Restaurants />} />
            <Route path="/restaurants/:id" element={<RestaurantMenu />} />
            <Route path="/cart" element={<Cart />} />
            <Route path="/orders" element={<CustomerOrders />} />
            <Route path="/insights" element={<AIInsights />} />
          </Route>

          <Route element={<ProtectedRoute roles={[ROLES.OWNER]} />}>
            <Route path="/owner" element={<OwnerDashboard />} />
            <Route path="/owner/orders" element={<OwnerOrders />} />
            <Route path="/owner/menu" element={<MenuManagement />} />
          </Route>

          <Route element={<ProtectedRoute roles={[ROLES.DELIVERY]} />}>
            <Route path="/delivery" element={<DeliveryDashboard />} />
          </Route>

          <Route path="/home" element={<Navigate to={user ? ROLE_HOME[user.role] : '/login'} replace />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </>
  );
}
