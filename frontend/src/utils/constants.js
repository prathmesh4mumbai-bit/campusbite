export const ROLES = {
  CUSTOMER: 'customer',
  OWNER: 'restaurant_owner',
  DELIVERY: 'delivery_partner',
};

export const ROLE_LABELS = {
  customer: 'Customer',
  restaurant_owner: 'Restaurant Owner',
  delivery_partner: 'Delivery Partner',
};

export const ROLE_HOME = {
  customer: '/',
  restaurant_owner: '/owner',
  delivery_partner: '/delivery',
};

export const ORDER_STATUSES = [
  'PLACED',
  'ACCEPTED',
  'PREPARING',
  'READY',
  'ASSIGNED',
  'OUT_FOR_DELIVERY',
  'DELIVERED',
  'CANCELLED',
  'REFUNDED',
];

// Happy-path steps shown in the tracker
export const TRACK_STEPS = ['PLACED', 'ACCEPTED', 'PREPARING', 'READY', 'ASSIGNED', 'OUT_FOR_DELIVERY', 'DELIVERED'];

export const STATUS_LABELS = {
  PLACED: 'Placed',
  ACCEPTED: 'Accepted',
  PREPARING: 'Preparing',
  READY: 'Ready',
  ASSIGNED: 'Rider assigned',
  OUT_FOR_DELIVERY: 'Out for delivery',
  DELIVERED: 'Delivered',
  CANCELLED: 'Cancelled',
  REFUNDED: 'Refunded',
};

export const EXAMPLE_QUESTIONS = [
  'Summarize my last five orders.',
  'Which of my orders are still not delivered?',
  'How much did I spend this week?',
  'Which food items have I ordered most frequently?',
];
