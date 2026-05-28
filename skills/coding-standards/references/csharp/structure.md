# C# / .NET — Architecture

The chosen pattern for C# / .NET projects: **flat business folders** inside one application project. Each business capability owns its endpoints, services, repository, models, and DTOs — vertical-slice style.

**Design goal:** adding, refactoring, or removing a feature touches *one folder*, not many. New features don't disturb existing ones. This is the same goal that drives Vertical Slice Architecture (Jimmy Bogard) — we just don't use the `Features/` wrapper folder, because the top-level folders inside the project are already the features.

This moves *away* from the common .NET layered template (separate `Domain`, `Application`, `Infrastructure`, `Api` projects). Layered Clean Architecture optimizes for strict dependency direction; for that you pay with *every new feature touching 4 projects*. That's the wrong trade for a team optimizing for feature-isolation. Layered DDD is right when the domain is genuinely complex (insurance, banking, regulated industries) — for most apps it's bureaucracy.

---

## The philosophy in one sentence

> One application project. Top-level folders inside it are business capabilities. Each capability owns every layer it needs — endpoints, services, repository, models, DTOs. Adding a feature = adding one folder. Cross-capability dependencies go through public types.

---

## Builds on `common/structure.md`

This file specializes the universal structural rules in `references/common/structure.md`. C# adds its own concerns: namespace-as-folder, vertical-slice (one-file-per-use-case) as an alternative grouping, async + nullability + cancellation hygiene, and the when-to-graduate-to-multi-project decision. Read `common/structure.md` first; the rules below add the C#-specific bits.

---

## Mandatory shape (solution layout)

```
MyApp.sln
src/
  MyApp/                              ← THE application project (one .csproj)
    Program.cs                        ← composition root, endpoint registration
    appsettings.json
    appsettings.Development.json

    Orders/                           ← 🛒 BUSINESS CAPABILITY
      OrderEndpoints.cs               ← minimal API endpoints (or OrdersController.cs)
      OrderService.cs                 ← orchestration / use cases
      OrderRepository.cs              ← EF Core queries
      Order.cs                        ← entity (EF mapped)
      OrderItem.cs                    ← entity inside the Order aggregate
      OrderStatus.cs                  ← enum or smart enum
      PlaceOrderRequest.cs            ← wire DTO (input)
      OrderResponse.cs                ← wire DTO (output)
      OrderPlaced.cs                  ← domain event (when used)
      NotEnoughStockException.cs

    Catalog/                          ← 📦 BUSINESS CAPABILITY
      ProductEndpoints.cs
      ProductService.cs
      ProductRepository.cs
      Product.cs
      Category.cs
      ProductResponse.cs

    Billing/                          ← 💳 BUSINESS CAPABILITY
      PaymentEndpoints.cs
      PaymentService.cs
      Payment.cs
      Invoice.cs
      StripeClient.cs                 ← capability-owned external client

    Identity/                         ← 🔐 BUSINESS CAPABILITY
      AuthEndpoints.cs
      AuthService.cs
      User.cs
      Role.cs
      SignInRequest.cs
      UserResponse.cs

    Shared/                           ← used by 3+ capabilities (Rule of Three)
      Http/
        ProblemDetailsMiddleware.cs
        RequestLoggingMiddleware.cs
      Data/
        AppDbContext.cs               ← EF Core DbContext (or split per capability when very large)
        DbContextExtensions.cs
      Errors/
        AppException.cs               ← base class for app-thrown exceptions
        NotFoundException.cs
      ValueObjects/
        Money.cs                      ← used widely enough to live here
      Auth/
        CurrentUser.cs                ← accessor for the authenticated principal

    MyApp.csproj
tests/
  MyApp.UnitTests/
  MyApp.IntegrationTests/
```

A multi-project split (e.g. `MyApp.Api`, `MyApp.Domain`, `MyApp.Infrastructure`) is **not** the default — only adopt it when:
- You need compile-time enforcement that one layer can't reference another (the team is large enough that this matters), or
- The domain is genuinely complex and warrants DDD's bounded contexts.

Both are real reasons; neither is the *starting* shape.

---

## CS-001 — Top-level folders inside the project are business capabilities

| Allowed at the top of the project | Forbidden |
|---|---|
| ✅ Business capability folders (`Orders/`, `Catalog/`, `Billing/`, `Identity/`) | ❌ `Controllers/` (all controllers together) |
| ✅ `Shared/` | ❌ `Services/` (all services together) |
| ✅ `Program.cs`, `appsettings.*`, `Properties/` | ❌ `Repositories/`, `Models/`, `Dtos/`, `Entities/` |
|  | ❌ `Domain/`, `Application/`, `Infrastructure/` (the DDD layering, when the domain isn't complex enough to warrant it) |
|  | ❌ `Features/` wrapper folder |

The namespace follows the folder: `Orders/OrderService.cs` is `MyApp.Orders.OrderService`. Add nothing to `MyApp.csproj`.

---

## CS-002 — Each capability folder owns every layer

| File pattern | Role |
|---|---|
| `<Resource>Endpoints.cs` | Minimal API endpoint registration (or `<Resource>Controller.cs` if using controllers) |
| `<Resource>Service.cs` | Orchestration / use cases |
| `<Resource>Repository.cs` | EF Core queries; only needed when queries don't belong on the entity or when abstraction is useful for testing |
| `<Resource>.cs` | EF Core entity (or domain object that EF maps to) |
| `<Verb><Resource>Request.cs` | Wire DTO (input) — validated at the boundary |
| `<Resource>Response.cs` | Wire DTO (output) — never expose entities directly |
| `<Event>.cs` | Domain event (past tense — `OrderPlaced`) |
| `<X>Exception.cs` | Capability-specific exception |

When you have many of one kind (10 endpoints, 8 events), introduce a subfolder *inside the capability* (`Orders/Events/`, `Orders/Endpoints/`) — only when warranted.

**Forbidden:** scattering one capability's pieces across `Controllers/`, `Services/`, `Repositories/`, `Models/`. That's package-by-layer.

### CS-002b — Optional: one file per use case (pure vertical slice)

For tighter feature isolation, group **by use case** rather than by file kind inside the capability. Each use case is one file containing its command, handler, validator, and endpoint registration together:

```
src/MyApp/Orders/
  PlaceOrder.cs        ← command record + handler + validator + endpoint mapping
  CancelOrder.cs
  RefundOrder.cs
  GetOrder.cs
  Order.cs             ← shared entity for the capability
  OrderRepository.cs   ← shared repository for the capability
  OrderStatus.cs
```

```csharp
// Orders/PlaceOrder.cs — the whole vertical slice in one file
namespace MyApp.Orders;

public sealed record PlaceOrderCommand(Guid CustomerId, List<OrderItemInput> Items);

public static class PlaceOrder
{
    public static void Map(IEndpointRouteBuilder app) =>
        app.MapPost("/orders", Handle).RequireAuthorization();

    public static async Task<IResult> Handle(
        PlaceOrderCommand command,
        OrderRepository orders,
        CancellationToken ct)
    {
        // validate, build entity, persist, return
        var order = Order.Place(command.CustomerId, command.Items);
        await orders.SaveAsync(order, ct);
        return Results.Created($"/orders/{order.Id}", OrderResponse.From(order));
    }
}
```

**Why this works for the design goal:** adding "Refund" is *literally* one file. Deleting it is one file. Refactoring it touches one file. Strict vertical slicing.

**When to choose this over CS-002:**
- ✅ Use one-file-per-use-case when the project has clear use-case boundaries and you want maximum feature isolation.
- ⚠️ Stay with the CS-002 grouping (separate Endpoints/Service/Repository files) when use cases share enough logic that splitting hurts readability, or when the team is more comfortable with classical layering inside the capability.

Pick one approach per project and stay consistent. Don't mix styles within the same capability.

---

## CS-003 — Behavior on entities when it's about the entity's data; in services when it's about orchestration

**Framework-boundary carve-out (see `common/objects-and-data.md` OD-005).** EF Core entities with persistence attributes (`[Key]`, `[ForeignKey]`, fluent-API configuration) and minimal-API request DTOs with validation attributes are intentionally hybrid by the framework's design. The line is still firm: business rules that *cross* the entity (charging payments, dispatching events, coordinating with other capabilities) belong in services, not on the entity.

Same placement rule as the Laravel doc — see `references/laravel/structure.md` LRV-003. In C#, the language helps you enforce it: use **private setters** and **factory methods** on entities to keep invariants intact.

```csharp
// ✅ Good — Order owns its own state transitions
public sealed class Order
{
    public Guid Id { get; private set; }
    public Guid CustomerId { get; private set; }
    public OrderStatus Status { get; private set; }
    private readonly List<OrderItem> _items = new();
    public IReadOnlyList<OrderItem> Items => _items;

    private Order() { } // EF Core needs a parameterless constructor

    public static Order Place(Guid customerId, IEnumerable<OrderItem> items)
    {
        var list = items.ToList();
        if (list.Count == 0) throw new EmptyOrderException();
        return new Order { Id = Guid.NewGuid(), CustomerId = customerId, Status = OrderStatus.Pending, _items = { ..list } };
    }

    public void Cancel(string reason)
    {
        if (Status == OrderStatus.Shipped) throw new CannotCancelShippedOrderException();
        Status = OrderStatus.Cancelled;
    }

    public decimal Total() => _items.Sum(i => i.Subtotal);
}

// ✅ Good — OrderService orchestrates across capabilities
public sealed class OrderService(
    OrderRepository orders,
    InventoryService inventory,
    PaymentService payments)
{
    public async Task<Order> PlaceAsync(PlaceOrderRequest request, CancellationToken ct)
    {
        await inventory.ReserveAsync(request.Items, ct);
        var order = Order.Place(request.CustomerId, request.Items.Select(i => OrderItem.Create(i.ProductId, i.Quantity)));
        await orders.SaveAsync(order, ct);
        await payments.ChargeAsync(order, ct);
        return order;
    }
}
```

EF Core can map entities with private setters and factory methods — set `UsePropertyAccessMode(PropertyAccessMode.Field)` in your `OnModelCreating` if needed. The added safety is worth the small config.

---

## CS-004 — Endpoints (or controllers) are thin

```csharp
// Orders/OrderEndpoints.cs
public static class OrderEndpoints
{
    public static void MapOrderEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/orders").RequireAuthorization();

        group.MapPost("/", async (PlaceOrderRequest request, OrderService orders, CancellationToken ct) =>
        {
            var order = await orders.PlaceAsync(request, ct);
            return Results.Created($"/orders/{order.Id}", OrderResponse.From(order));
        })
        .WithValidationFilter<PlaceOrderRequest>();   // whichever validation approach the project uses

        group.MapPost("/{id:guid}/cancel", async (Guid id, CancelOrderRequest request, OrderService orders, CancellationToken ct) =>
        {
            await orders.CancelAsync(id, request.Reason, ct);
            return Results.NoContent();
        });
    }
}
```

`Program.cs` calls `app.MapOrderEndpoints();` per capability. Each capability registers its own endpoints; `Program.cs` doesn't grow with the app.

**Forbidden in endpoints/controllers:**
- ❌ Direct `DbContext` calls
- ❌ Business rules (`if (order.Customer.IsVip) { ... }`)
- ❌ Sending notifications, dispatching jobs
- ❌ Wire DTO ↔ entity conversion beyond a one-liner `Response.From(entity)` mapping (push complex mapping into the response DTO's static factory)

---

## CS-005 — Wire DTOs separate from entities

Never return an EF entity from an endpoint. Entities have circular references, lazy-loadable navigation properties, and shape that leaks DB choices. Use a response DTO (record):

```csharp
public sealed record OrderResponse(
    Guid Id,
    Guid CustomerId,
    string Status,
    decimal Total,
    IReadOnlyList<OrderItemResponse> Items)
{
    public static OrderResponse From(Order order) => new(
        order.Id,
        order.CustomerId,
        order.Status.ToString(),
        order.Total(),
        order.Items.Select(OrderItemResponse.From).ToList()
    );
}
```

Input DTOs (`PlaceOrderRequest`) are validated at the boundary — using DataAnnotations, a validation library, or minimal-API validation filters — never trust the wire shape inside services.

---

## CS-006 — Async, cancellation, nullability everywhere

Non-negotiable for new C# code:

- **Nullable reference types** enabled in `MyApp.csproj` (`<Nullable>enable</Nullable>`). No silent `null` propagation.
- **Async/await** end-to-end. Never `.Result`, `.Wait()`, or `.GetAwaiter().GetResult()` — they deadlock under sync contexts and starve the thread pool.
- **`CancellationToken`** as the last parameter of every async method that crosses a layer boundary.
- **`async void`** only for event handlers. Anywhere else it leaks unhandled exceptions.
- **`sealed`** classes by default. Open them only when you have a real polymorphism design.
- **`ConfigureAwait(false)`** in library code (not application code; ASP.NET Core has no sync context).

```csharp
// ✅ Good
public async Task<Order?> FindByIdAsync(Guid id, CancellationToken ct)
    => await _db.Orders.Include(o => o.Items).FirstOrDefaultAsync(o => o.Id == id, ct);

// ❌ Bad
public async void HandleOrder(Guid id) { ... }                       // async void
public Order? FindById(Guid id) => FindByIdAsync(id).Result;          // sync-over-async
```

---

## CS-007 — Primitive obsession: wrap when it matters

A `Guid` can be a `UserId`, an `OrderId`, or a `ProductId`. A `string` can be an email, a country code, or a slug. Mixing them up compiles fine — and ships bugs.

For high-traffic value types, wrap with `record struct`:

```csharp
public readonly record struct OrderId(Guid Value)
{
    public static OrderId NewId() => new(Guid.NewGuid());
    public override string ToString() => Value.ToString();
}
```

**Apply selectively.** Wrapping every `Guid` is over-engineering. Wrap when:
- The type is passed around enough that mix-ups would compile and ship (an `OrderId` reaching a method expecting `UserId`).
- The type has invariants (`Email` should fail to construct on invalid format).
- The type drives behavior (`Money` enforcing currency match in `Add`).

For one-off internal IDs that never cross boundaries, raw `Guid` is fine.

---

## CS-008 — `Shared/` requires three users

Rule of Three. Move code to `Shared/` only when 3+ capabilities use it:

| Allowed in `Shared/` | Forbidden |
|---|---|
| ✅ `Shared/Data/AppDbContext.cs` (one DbContext serves the whole app) | ❌ `Shared/Helpers.cs` (junk drawer) |
| ✅ `Shared/Http/ProblemDetailsMiddleware.cs` | ❌ `Shared/Models.cs` mega-file |
| ✅ `Shared/Errors/AppException.cs` (base class) | ❌ A service only `Orders/` and `Catalog/` use — duplicate until the third user appears |
| ✅ `Shared/ValueObjects/Money.cs` (used widely) |  |
| ✅ `Shared/Auth/CurrentUser.cs` (every capability needs the principal) |  |

**Never start in `Shared/`.** Write the helper in the first capability. Duplicate in the second. Extract on the third.

---

## CS-009 — Dependency injection: capability owns its registrations

Each capability provides an extension method that registers its services:

```csharp
// Orders/OrdersServiceCollectionExtensions.cs
public static class OrdersServiceCollectionExtensions
{
    public static IServiceCollection AddOrders(this IServiceCollection services)
    {
        services.AddScoped<OrderService>();
        services.AddScoped<OrderRepository>();
        return services;
    }
}
```

`Program.cs` calls each capability's `Add<Capability>()`:

```csharp
var builder = WebApplication.CreateBuilder(args);
builder.Services
    .AddOrders()
    .AddCatalog()
    .AddBilling()
    .AddIdentity()
    .AddSharedInfrastructure(builder.Configuration);

var app = builder.Build();
app.MapOrderEndpoints();
app.MapCatalogEndpoints();
app.MapBillingEndpoints();
app.MapAuthEndpoints();
app.Run();
```

`Program.cs` reads as a manifest of capabilities — not a 200-line registration soup.

---

## CS-010 — Naming

| Type | Convention | Example |
|---|---|---|
| Capability folder | `PascalCase`, plural | `Orders/`, `Catalog/`, `Identity/` |
| Namespace | matches folder | `MyApp.Orders` |
| Endpoint class | `<Resource>Endpoints` | `OrderEndpoints` |
| Controller (if used) | `<Resource>Controller` | `OrdersController` |
| Service | `<Resource>Service` | `OrderService` |
| Repository | `<Resource>Repository` | `OrderRepository` |
| Entity | `<Resource>`, singular | `Order`, `Product` |
| Wire DTO (input) | `<Verb><Resource>Request` | `PlaceOrderRequest` |
| Wire DTO (output) | `<Resource>Response` | `OrderResponse` |
| Event (past tense) | `<Resource><PastVerb>` | `OrderPlaced`, `PaymentCaptured` |
| Exception | `<Specific>Exception` | `NotEnoughStockException` |
| DI extension | `Add<Capability>` | `AddOrders` |
| Endpoint mapping | `Map<Resource>Endpoints` | `MapOrderEndpoints` |
| Async method | `<Verb>Async` | `PlaceAsync`, `FindByIdAsync` |
| Interface | `IPascalCase` | `IPaymentGateway` (keep the `I` — it's the C# convention) |

---

## When to graduate to multi-project DDD

You'll know it's time when the **second** of these is true:

1. Your domain has genuinely complex rules (regulatory, financial, scheduling with constraints — not "form → API → DB").
2. The team is large enough that you need compile-time enforcement that the HTTP layer can't reach into the persistence layer.
3. You want bounded contexts because two different parts of the system genuinely model the same noun differently (a `Customer` in Sales has nothing to do with a `Customer` in Support).

Until then, the flat-capability shape is faster to build in, easier to onboard, and easier to refactor. The promotion path is mechanical: each capability folder becomes its own set of projects (`<Cap>.Domain`, `<Cap>.Application`, `<Cap>.Infrastructure`, `<Cap>.Api`) only when needed, and only for the capabilities that warrant it.

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| Top-level `Controllers/`, `Services/`, `Models/`, `Repositories/` folders | Package by layer — capability spread across folders |
| Endpoints/controllers with business logic or direct `DbContext` access | Should delegate to service |
| Returning EF entities from endpoints | Use response DTOs |
| Public setters on aggregate entities | Allows callers to bypass invariants |
| Anemic entities with all logic in services | Behavior tied to entity data belongs on the entity |
| `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` | Deadlock risk, thread pool starvation |
| `async void` outside event handlers | Crashes the process on unhandled exceptions |
| Missing `CancellationToken` on async public APIs | Operations cannot be cancelled |
| `<Nullable>disable</Nullable>` in new projects | Loses null safety |
| One giant `Program.cs` with every service registration inlined | Move registrations into capability extension methods |
| `Domain/`, `Application/`, `Infrastructure/`, `Features/` wrappers | The flat-capability shape doesn't use them |
| Generic `IRepository<T>` serving every capability | Repositories are per-capability with domain-shaped methods |
| Cross-capability deep imports into `*.Internal` types | Should communicate via public services or events |
| `Helpers` static class in `Shared/` | Name helpers by what they do |

---

## Review checklist

```
Structure
  □ Top-level folders inside the project are business capabilities
  □ Program.cs reads as a manifest of capabilities
  □ Shared/ contains only code used by 3+ capabilities
  □ No top-level Controllers/, Services/, Models/, Repositories/
  □ No Domain/Application/Infrastructure wrappers
  □ No Features/ wrapper

Per capability
  □ Endpoints, Service, Repository, Entity, Request DTO, Response DTO co-located
  □ Capability has Add<Capability>() DI extension
  □ Capability registers its own endpoint group via Map<X>Endpoints()

Behavior placement
  □ Entity behavior is about the entity's own data
  □ Cross-cutting workflows in services
  □ Cross-capability side effects via events when possible

Language hygiene
  □ Nullable enabled
  □ Async + CancellationToken end-to-end
  □ No sync-over-async
  □ Sealed classes by default
  □ Private setters on aggregate entities

HTTP boundary
  □ Endpoints/controllers thin
  □ DTOs validated at the boundary
  □ Response DTOs separate from entities
  □ Entities never returned directly
```
