---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep]
model: opus
runs: 3
plugins: [../..]
tags: [typescript, review, none]
---
Can you review this before I merge?

```ts
interface Customer {
  id: string;
  name: string;
  email: string;
  shippingAddress: string;
}

interface OrderItem {
  sku: string;
  priceCents: number;
  quantity: number;
}

interface Order {
  id: string;
  items: OrderItem[];
  express: boolean;
  giftWrap: boolean;
  status: "pending" | "paid";
}

interface CheckoutDeps {
  customers: { findById(id: string): Promise<Customer> };
  orders: { save(order: Order): Promise<void> };
  payments: { charge(customerId: string, amountCents: number): Promise<void> };
  mailer: { sendReceipt(to: string, orderId: string, amountCents: number): Promise<void> };
  shipping: { createLabel(request: Record<string, string | boolean>): Promise<void> };
}

export class CheckoutService {
  constructor(private readonly deps: CheckoutDeps) {}

  async checkout(customerId: string, order: Order): Promise<Order> {
    if (order.items.length === 0) {
      throw new Error("Cannot check out an empty order");
    }
    const totalCents = order.items.reduce((sum, item) => sum + item.priceCents * item.quantity, 0);
    const customer: any = await this.deps.customers.findById(customerId);

    try {
      await this.deps.payments.charge(customer.id, totalCents);
    } catch (error) {
      console.warn("payment failed", error);
    }

    order.status = "paid";
    await this.deps.orders.save(order);
    await this.deps.mailer.sendReceipt(customer.emailAddress, order.id, totalCents);
    await this.createShipment(order.id, customer.shippingAddress, order.express, order.giftWrap, true, "ups");
    return order;
  }

  private async createShipment(
    orderId: string,
    address: string,
    express: boolean,
    giftWrap: boolean,
    signatureRequired: boolean,
    carrier: string,
  ): Promise<void> {
    await this.deps.shipping.createLabel({ orderId, address, express, giftWrap, signatureRequired, carrier });
  }
}
```
