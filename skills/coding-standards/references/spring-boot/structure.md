# Spring Boot — Architecture

The chosen pattern for Spring Boot projects (Java or Kotlin): **package by feature** — top-level packages under the application's root package are business capabilities, each containing its controller, service, repository, entities, and DTOs. Spring's component scanning and DI container do the wiring; the rules here keep the layout from drifting back into package-by-layer.

---

## The philosophy in one sentence

> One package per business capability under the root package. Each package owns every layer it needs — controller, service, repository, entities, request/response DTOs. Cross-package dependencies use Spring beans, never deep references into another package's internals.

---

## Builds on `common/structure.md`

This file specializes the universal structural rules in `references/common/structure.md`. Spring Boot adds DI via annotations (`@Service`, `@Repository`, `@RestController`), Jakarta validation on request DTOs, JPA entities, Spring profiles for configuration, and the AutoConfiguration ecosystem. Read `common/structure.md` first.

---

## Mandatory shape (Java; the Kotlin layout is identical)

```
src/main/java/com/example/myapp/
  MyAppApplication.java               ← @SpringBootApplication entrypoint

  orders/                             ← 🛒 BUSINESS CAPABILITY
    OrderController.java              ← @RestController
    OrderService.java                 ← @Service — orchestration / use cases
    OrderRepository.java              ← @Repository — Spring Data JPA
    Order.java                        ← @Entity — JPA entity
    OrderItem.java                    ← @Entity
    OrderStatus.java                  ← enum
    PlaceOrderRequest.java            ← request DTO (with Jakarta Validation)
    OrderResponse.java                ← response DTO (record)
    OrderPlacedEvent.java             ← Spring application event
    OrdersConfiguration.java          ← @Configuration (when capability has its own beans)

  catalog/                            ← 📦 BUSINESS CAPABILITY
    ProductController.java
    ProductService.java
    ProductRepository.java
    Product.java
    Category.java
    ...

  identity/                           ← 🔐 BUSINESS CAPABILITY
    AuthController.java
    SecurityConfiguration.java        ← @Configuration extending Spring Security
    User.java
    Role.java
    SignInRequest.java

  shared/                             ← cross-cutting (3+ capabilities)
    web/
      GlobalExceptionHandler.java     ← @RestControllerAdvice
      ProblemDetailMapper.java
    persistence/
      JpaConfig.java                  ← @EnableJpaRepositories, audit listeners
      BaseAuditableEntity.java        ← shared timestamp/audit shape (optional)
    error/
      AppException.java               ← base for app-thrown exceptions
      NotFoundException.java
    config/
      AppProperties.java              ← @ConfigurationProperties
    web/CurrentUser.java              ← argument resolver for the authenticated principal

src/main/resources/
  application.yml                     ← default profile
  application-dev.yml
  application-prod.yml
  application-test.yml
  db/migration/                       ← Flyway (or Liquibase)
    V1__init.sql
    V2__add_orders.sql

src/test/java/com/example/myapp/
  orders/
    OrderServiceTest.java
    OrderControllerTest.java
  ...
```

---

## SB-001 — Top-level packages are business capabilities

Under the application's root package, every direct child package is a business capability — `orders`, `catalog`, `identity`, `billing`. **Forbidden** at the top: `controllers`, `services`, `repositories`, `models`, `dtos` as siblings of the application class.

| ✅ Allowed | ❌ Forbidden |
|---|---|
| `myapp.orders`, `myapp.catalog`, `myapp.identity` (capabilities) | `myapp.controllers`, `myapp.services`, `myapp.entities` |
| `myapp.shared` for cross-cutting infrastructure | `myapp.utils`, `myapp.helpers` |
| `myapp.config` for app-wide `@Configuration` (when not capability-specific) | `myapp.web` as a layer of every controller |

Same rule as the rest of this skill — see `common/structure.md` ST-001.

---

## SB-002 — Three-layer split inside each capability

Spring's component stereotypes (`@RestController`, `@Service`, `@Repository`) make the layer split visible at a glance:

| Layer | Annotation | Owns | Does NOT own |
|---|---|---|---|
| Controller | `@RestController` | HTTP plumbing, request parsing, status codes | Business rules, persistence |
| Service | `@Service` | Orchestration: validates, coordinates repositories, raises events | Direct JDBC/JPA queries, HTTP details |
| Repository | `@Repository` (or `extends JpaRepository`) | Persistence per aggregate | Business rules |
| Entity | `@Entity` | Invariants tied to the entity's data | Cross-aggregate workflows |

```java
@RestController
@RequestMapping("/orders")
@RequiredArgsConstructor
public class OrderController {
    private final OrderService orders;

    @PostMapping
    public ResponseEntity<OrderResponse> place(@Valid @RequestBody PlaceOrderRequest request,
                                               @CurrentUser User user) {
        Order order = orders.place(user, request);
        return ResponseEntity.status(201).body(OrderResponse.from(order));
    }
}

@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository repo;
    private final PaymentClient payments;
    private final ApplicationEventPublisher events;

    @Transactional
    public Order place(User user, PlaceOrderRequest request) {
        if (request.items().isEmpty()) throw new EmptyOrderException();
        Order order = Order.place(user.getId(), request.items());
        repo.save(order);
        payments.charge(order);
        events.publishEvent(new OrderPlacedEvent(order));
        return order;
    }
}
```

**Forbidden:** controllers calling repositories directly. **Forbidden:** services manipulating `HttpServletRequest`/`HttpServletResponse`.

---

## SB-003 — Entities own behavior tied to their data

**Framework-boundary carve-out (see `common/objects-and-data.md` OD-005).** JPA entities carry `@Entity`, `@Column`, `@Id`, `@OneToMany` etc. — they're intentionally hybrid by the framework's design. The line is still firm: cross-cutting workflows live in services, not on the entity.

```java
@Entity
@Table(name = "orders")
public class Order {
    @Id @GeneratedValue
    private UUID id;

    @Enumerated(EnumType.STRING)
    private OrderStatus status;

    @OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderItem> items = new ArrayList<>();

    protected Order() {} // JPA requirement

    public static Order place(UUID customerId, List<OrderItemInput> items) {
        if (items.isEmpty()) throw new EmptyOrderException();
        var order = new Order();
        order.id = UUID.randomUUID();
        order.status = OrderStatus.PENDING;
        order.items.addAll(items.stream().map(OrderItem::of).toList());
        return order;
    }

    public void cancel(String reason) {
        if (status == OrderStatus.SHIPPED) throw new CannotCancelException();
        status = OrderStatus.CANCELLED;
    }

    public BigDecimal total() {
        return items.stream().map(OrderItem::subtotal).reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    // No public setters — invariants enforced by factory + behavior methods.
}
```

**Forbidden:** Lombok's `@Data` or `@Setter` on aggregate entities. That breaks invariants by exposing public setters for every field. Use `@Getter` on read-only fields, factory methods + behavior methods for mutation. (Lombok's `@NoArgsConstructor(access = PROTECTED)` is fine for the JPA-required constructor.)

For **Kotlin**, use data classes with `private val` constructor params for ID/timestamps and `val` for read-only attributes; mutations go through methods that copy or `apply`.

---

## SB-004 — DTOs at the boundary; never return entities directly

JPA entities have circular relations, lazy proxies, and shape that leaks DB choices. **Always map to a response DTO** before returning from a controller. Use Java 17+ records for response DTOs:

```java
public record OrderResponse(
        UUID id,
        UUID customerId,
        String status,
        BigDecimal total,
        List<OrderItemResponse> items) {

    public static OrderResponse from(Order order) {
        return new OrderResponse(
                order.getId(),
                order.getCustomerId(),
                order.getStatus().name(),
                order.total(),
                order.getItems().stream().map(OrderItemResponse::from).toList());
    }
}
```

Request DTOs carry Jakarta validation annotations:

```java
public record PlaceOrderRequest(
        @NotEmpty List<@Valid OrderItemInput> items,
        @NotNull UUID shippingAddressId) {}

public record OrderItemInput(
        @NotNull UUID productId,
        @Positive int quantity) {}
```

The controller uses `@Valid @RequestBody` so Spring runs validation before the handler body. Validation failures are caught by the global handler (SB-007) and translated into Problem Details.

---

## SB-005 — Repositories are per-aggregate; not generic `Repository<T>`

Spring Data lets you extend `JpaRepository<T, ID>` to get CRUD methods for free. That's fine — but the *project's* repository should still be capability-shaped, with **domain-named methods** that callers actually use:

```java
public interface OrderRepository extends JpaRepository<Order, UUID> {
    Optional<Order> findByCustomerIdAndStatus(UUID customerId, OrderStatus status);
    List<Order> findRecentForCustomer(UUID customerId, Pageable pageable);
    // queries that hide JPQL/Specification complexity behind a named method
}
```

**Forbidden:** a generic `BaseRepository<T>` that every capability extends and that exposes the same flat `findAll`, `save`, `delete` to controllers. That collapses to the anti-pattern in `common/structure.md` ST-006 (generic names everywhere). Each capability has *its* repository with *its* domain methods.

For complex queries, prefer **Specifications**, **JPQL @Query**, or **QueryDSL** over hand-rolled criteria. Put the complex query *on the repository*, not on the controller or service.

---

## SB-006 — Profiles and configuration

Spring's profile system (`application.yml`, `application-{profile}.yml`) is the right place for environment-specific config. **Forbidden:** `System.getenv("X")` scattered through feature code.

Use `@ConfigurationProperties` to bind typed config:

```java
@ConfigurationProperties(prefix = "myapp.payment")
public record PaymentProperties(
        @NotBlank String apiKey,
        @NotNull URI endpoint,
        @Positive int retryCount) {}

@SpringBootApplication
@EnableConfigurationProperties(PaymentProperties.class)
public class MyAppApplication { }
```

Validated at boot. The bean is injectable into any service that needs it. Required properties absent → application refuses to start. That's the desired failure mode.

**Profiles to define:**

| Profile | Use |
|---|---|
| `default` | Defaults shared across environments |
| `dev` | Local development overrides |
| `test` | Integration test config (H2 / Testcontainers) |
| `prod` | Production overrides |

---

## SB-007 — Centralized error handling via `@RestControllerAdvice`

Define an app exception hierarchy and a global handler that maps to RFC 9457 Problem Details (Spring 6 / Boot 3 has built-in support via `ProblemDetail`):

```java
public abstract class AppException extends RuntimeException {
    public abstract HttpStatus status();
    public abstract String code();
    protected AppException(String message) { super(message); }
}

public class NotFoundException extends AppException {
    @Override public HttpStatus status() { return HttpStatus.NOT_FOUND; }
    @Override public String code() { return "not_found"; }
    public NotFoundException(String message) { super(message); }
}
```

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(AppException.class)
    public ProblemDetail handleApp(AppException ex) {
        var pd = ProblemDetail.forStatusAndDetail(ex.status(), ex.getMessage());
        pd.setProperty("code", ex.code());
        return pd;
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleValidation(MethodArgumentNotValidException ex) {
        var pd = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "validation_failed");
        pd.setProperty("fields", ex.getBindingResult().getFieldErrors().stream()
                .map(f -> Map.of("field", f.getField(), "error", f.getDefaultMessage()))
                .toList());
        return pd;
    }
}
```

Services throw domain exceptions; the handler translates. **No `ResponseEntity.status(404)` returns scattered across controllers.** That's `common/error-handling.md` EH-002 applied to Spring.

---

## SB-008 — Capability beans live near their capability

For complex capabilities that need their own beans (HTTP clients, scheduled jobs, custom interceptors), put a `@Configuration` class inside the capability package:

```java
@Configuration
public class OrdersConfiguration {

    @Bean
    PaymentClient paymentClient(PaymentProperties props, WebClient.Builder builder) {
        return new PaymentClient(builder.baseUrl(props.endpoint().toString()).build(), props.apiKey());
    }

    @Bean
    OrderShippingScheduler shippingScheduler(OrderRepository repo, ShippingClient shipping) {
        return new OrderShippingScheduler(repo, shipping);
    }
}
```

**Forbidden:** stuffing every bean into one giant `AppConfiguration` at the root. That's an analogue of the "god service registration" — every capability owns its own beans, registered next to the capability code.

`@SpringBootApplication`'s component scanning picks up annotated classes in the root package and its descendants — no manual registration needed.

---

## SB-009 — Migrations are part of the codebase

Use Flyway (or Liquibase) for schema migrations. Migrations live in `src/main/resources/db/migration/` and follow Flyway's naming (`V1__init.sql`, `V2__add_orders.sql`). They run on application startup; production deployments include the migrations along with the JAR.

**Never edit a merged migration.** Schema history is append-only. New requirement → new migration file.

**Don't use `spring.jpa.hibernate.ddl-auto=update` in production.** Migrations are explicit, reviewed, and versioned; auto-DDL silently drifts schemas.

---

## SB-010 — Cross-capability dependencies via beans only

Capability A's controller calling `B.SomeInternalClass` directly is forbidden. Instead, capability A injects a Spring bean exposed by capability B:

```java
// ❌ Forbidden
import com.example.myapp.identity.internal.LegacyAuthMapper;

// ✅ Allowed
@Service
public class OrderService {
    private final UserDirectory userDirectory;  // bean from identity capability
    // ...
}
```

If capability A needs broad access to capability B's domain, that's a design smell — usually the missing concept is a shared *abstraction* in `shared/`, or events between capabilities. Don't normalize cross-capability reach-in.

Enforce with **ArchUnit**:

```java
@AnalyzeClasses(packages = "com.example.myapp", importOptions = DoNotIncludeTests.class)
class ArchitectureTests {
    @ArchTest
    static final ArchRule capabilitiesDoNotDependOnEachOtherInternally =
        noClasses().that().resideInAPackage("..orders..")
            .should().dependOnClassesThat().resideInAnyPackage("..catalog.internal..", "..identity.internal..");
}
```

---

## SB-011 — Naming

| Type | Convention | Example |
|---|---|---|
| Capability package | `lowercase`, plural | `orders`, `catalog`, `identity` |
| Application class | `<App>Application` | `MyAppApplication` |
| Controller | `<Resource>Controller` | `OrderController` |
| Service | `<Resource>Service` | `OrderService` |
| Repository | `<Resource>Repository` | `OrderRepository` |
| Entity | `<Resource>` singular | `Order`, `Product` |
| Request DTO | `<Verb><Resource>Request` | `PlaceOrderRequest` |
| Response DTO | `<Resource>Response` | `OrderResponse` |
| Event | `<Resource><PastVerb>Event` | `OrderPlacedEvent`, `PaymentCapturedEvent` |
| Exception | `<Specific>Exception` | `NotEnoughStockException` |
| Configuration class | `<Scope>Configuration` | `OrdersConfiguration`, `SecurityConfiguration` |
| Properties class | `<Scope>Properties` | `PaymentProperties` |

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| Top-level `controllers/`, `services/`, `repositories/` packages | Package by layer — the anti-pattern this design replaces |
| Controllers with business logic or direct repository calls | Use a service |
| Returning JPA entities from controllers | Use a response DTO; entities leak lazy proxies and DB shape |
| Lombok `@Data` or `@Setter` on aggregate entities | Breaks invariants — use factory methods and explicit behavior methods |
| `spring.jpa.hibernate.ddl-auto=update` in production config | Drift; use Flyway or Liquibase migrations |
| `System.getenv("X")` scattered through code | Use `@ConfigurationProperties` |
| `ResponseEntity.badRequest()...` returns scattered in controllers | Throw a domain exception; handle in `@RestControllerAdvice` |
| Generic `BaseRepository<T>` extended by every capability | Each repository is per-aggregate with domain methods |
| Cross-capability `import ...internal...` | Use a bean exposed by the other capability |
| `MyAppApplication` directly registering 50 beans | Beans live near their capability in `@Configuration` classes |
| Editing a merged Flyway migration | Migrations are append-only |
| `@Transactional` on controller methods | Transaction boundary is the service layer |
| `shared/utils/Helpers.java` | Junk drawer; name files by what they do |

---

## Review checklist

```
Structure
  □ Top-level packages are business capabilities, not layers
  □ Each capability has Controller, Service, Repository, Entity, request/response DTOs
  □ shared/ contains only code used by 3+ capabilities
  □ Capability owns its own @Configuration (when it has beans)

HTTP boundary
  □ Controllers thin — parse, call service, shape response
  □ Request DTOs use Jakarta Validation (@Valid)
  □ Response DTOs (records) — entities never returned directly

Domain
  □ Entities own invariants tied to their data
  □ Factory methods construct aggregates with valid state
  □ No public setters on aggregate fields
  □ Cross-cutting workflows in services or events

Persistence
  □ Repositories are per-aggregate with domain methods
  □ No generic BaseRepository<T>
  □ Schema migrations via Flyway/Liquibase
  □ No ddl-auto=update in production

Error handling
  □ AppException hierarchy in shared/error/
  □ GlobalExceptionHandler (@RestControllerAdvice) translates to ProblemDetail
  □ No raw ResponseEntity.status(400) in controllers

Configuration
  □ @ConfigurationProperties for typed env
  □ Profiles (dev/test/prod) for environment overrides
  □ No System.getenv scattered through code

Cross-capability
  □ Reference other capabilities via injected beans only
  □ No reach into other capabilities' internal classes
  □ ArchUnit rules enforce package boundaries
```
