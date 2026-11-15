import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from './AuthContext';

const CartContext = createContext(null);
const CART_KEY = 'campusbite_cart';
const EMPTY = { restaurant: null, items: [] };

function loadCart() {
  try {
    const saved = JSON.parse(localStorage.getItem(CART_KEY));
    if (saved && Array.isArray(saved.items)) return saved;
  } catch {
    /* ignore corrupt data */
  }
  return EMPTY;
}

export function CartProvider({ children }) {
  const { user } = useAuth();
  const [cart, setCart] = useState(loadCart);

  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
  }, [cart]);

  // A different person logging in (or logging out) must not inherit the previous cart.
  const previousUserId = useRef(user?.id);
  useEffect(() => {
    if (previousUserId.current !== user?.id) setCart(EMPTY);
    previousUserId.current = user?.id;
  }, [user?.id]);

  const addItem = useCallback(
    (dish, restaurant) => {
      if (cart.restaurant && cart.restaurant.id !== restaurant.id && cart.items.length > 0) {
        const ok = window.confirm(
          `Your cart has items from ${cart.restaurant.name}. Start a new cart with ${restaurant.name} instead?`,
        );
        if (!ok) return;
        setCart({ restaurant: { id: restaurant.id, name: restaurant.name }, items: [{ ...pick(dish), quantity: 1 }] });
        return;
      }
      setCart((prev) => {
        const existing = prev.items.find((i) => i.menu_item_id === dish.id);
        const items = existing
          ? prev.items.map((i) => (i.menu_item_id === dish.id ? { ...i, quantity: Math.min(i.quantity + 1, 50) } : i))
          : [...prev.items, { ...pick(dish), quantity: 1 }];
        return { restaurant: { id: restaurant.id, name: restaurant.name }, items };
      });
    },
    [cart],
  );

  const setQuantity = useCallback((menuItemId, quantity) => {
    setCart((prev) => {
      const items =
        quantity <= 0
          ? prev.items.filter((i) => i.menu_item_id !== menuItemId)
          : prev.items.map((i) => (i.menu_item_id === menuItemId ? { ...i, quantity: Math.min(quantity, 50) } : i));
      return items.length ? { ...prev, items } : EMPTY;
    });
  }, []);

  const removeItem = useCallback((menuItemId) => setQuantity(menuItemId, 0), [setQuantity]);
  const clearCart = useCallback(() => setCart(EMPTY), []);

  const value = useMemo(() => {
    const count = cart.items.reduce((n, i) => n + i.quantity, 0);
    const total = cart.items.reduce((sum, i) => sum + i.price * i.quantity, 0);
    return { ...cart, count, total, addItem, setQuantity, removeItem, clearCart };
  }, [cart, addItem, setQuantity, removeItem, clearCart]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

const pick = (dish) => ({ menu_item_id: dish.id, name: dish.name, price: dish.price });

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart must be used inside <CartProvider>');
  return ctx;
}
