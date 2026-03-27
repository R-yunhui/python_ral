# Spring / Spring Boot / Spring Cloud 高频面试题（IoC · AOP · 自动配置 · 微服务组件）

> 面向 **Spring Framework 6.x + Spring Boot 3.x + Spring Cloud 2023.x / 2024.x**（**Jakarta EE 命名空间**）；具体注解与默认行为以项目依赖版本为准。综合近年技术社区面经（注册配置、网关、熔断限流、可观测性）与官方演进方向整理，**偏实战追问可落到源码概念与运维取舍**。

---

## 目录

1. [Spring 核心：IoC 与 Bean](#一spring-核心ioc-与-bean)
2. [Spring MVC 与 Web](#二spring-mvc-与-web)
3. [AOP](#三aop)
4. [Spring Boot：启动与自动配置](#四spring-boot启动与自动配置)
5. [Spring Boot 3 与生态升级](#五spring-boot-3-与生态升级)
6. [Spring Cloud：体系与组件选型](#六spring-cloud体系与组件选型)
7. [服务调用、负载均衡与容错](#七服务调用负载均衡与容错)
8. [网关、安全与配置](#八网关安全与配置)
9. [可观测性、测试与部署](#九可观测性测试与部署)
10. [实战场景题](#十实战场景题)
11. [面经高频补充](#十一面经高频补充)
12. [自测清单](#十二自测清单)

---

## 一、Spring 核心：IoC 与 Bean

### 1. IoC 与 DI 是什么？和「工厂模式」差在哪？

**答：** **IoC（控制反转）**：对象的生命周期与依赖关系由 **容器** 管理，业务类不自己 `new` 依赖。**DI（依赖注入）** 是实现 IoC 的主要手段：构造器注入、setter 注入、字段注入（不推荐在核心业务域滥用）。  
与手写工厂相比：**容器** 负责 **作用域、生命周期回调、循环依赖处理（有限场景）、AOP 代理** 等横切能力；工厂偏 **显式创建**，Spring 偏 **声明式装配 + 约定**。

---

### 2. `@Component`、`@Service`、`@Repository`、`@Controller` 区别？

**答：** **都是 stereotype**，最终都会注册为 Bean；差异主要在 **语义分层** 与 **少量附加行为**：  
- **`@Repository`**：数据访问层语义，**历史上** 与持久化异常 **`PersistenceExceptionTranslation`（将底层异常转为 `DataAccessException`）** 相关。  
- **`@Service`**：业务层语义。  
- **`@Controller` / `@RestController`**：Web 层；`@RestController` = `@Controller` + `@ResponseBody`。  
**面试收束：** 分层可读性 + AOP/异常翻译等 **边缘增强**，**不要** 过度迷信「换注解就能改行为」。

---

### 3. Bean 作用域有哪些？单例 Bean 线程安全吗？

**答：** 常用 **`singleton`（默认）**、`prototype`、`request`、`session`、`application`（Servlet）、`websocket` 等。  
**单例 Bean 本身不等于线程安全**：若 Bean **无可变共享状态**（仅依赖无状态 DAO），则安全；若 **有成员变量缓存** 等，需 **`prototype`** 或 **加锁/ThreadLocal（慎用）** / 把可变状态下沉到 **方法局部**。**原型作用域** 的 Bean 若被 **单例 Bean 注入**，需注意 **lookup 方法注入** 或 **`ObjectProvider`** 每次获取新实例。

---

### 4. Bean 生命周期关键节点口头描述？

**答：** 典型链路（概念顺序）：**实例化 → 属性注入 → `BeanNameAware` / `BeanFactoryAware` 等 aware → `BeanPostProcessor.postProcessBeforeInitialization` → `@PostConstruct` / `InitializingBean.afterPropertiesSet` / 自定义 init → `postProcessAfterInitialization` → Bean 可用 → 容器关闭时 `@PreDestroy` / `DisposableBean.destroy`。  
**追问点：** AOP 代理往往在 **后置处理器** 阶段包装 **目标 Bean**，因此 **同类内自调用** 不走代理（面试常考）。

---

### 5. 循环依赖如何解决？为什么构造器注入环不行？

**答：** **默认可行的单例 + setter/字段注入** 场景，Spring 用 **三级缓存**（singletonObjects / earlySingletonObjects / singletonFactories）提前暴露 **早期引用**，再完成属性填充。**构造器循环依赖** 无法在创建前暴露实例 → **通常直接失败**（可用 `@Lazy` 打破、或重构层次）。**`prototype`** 循环依赖 **不支持**。**面试警示：** 循环依赖是 **设计味道**，能重构优先重构。

---

### 6. `@Autowired` 注入规则？与 `@Resource`、`@Inject`？

**答：** **`@Autowired`**：默认 **按类型**，多实现时配合 **`@Primary`** / **`@Qualifier`** / **`@Order`**（集合注入顺序）。**`@Resource`（JSR-250）**：默认 **按名称** 再按类型。`@Inject`（JSR-330）+ `@Named` 类似 Guice 风格。  
**推荐：** **构造器注入** 便于 **不可变依赖** 与 **单元测试**。

---

### 7. `FactoryBean` 与 `BeanFactory`？

**答：** **`BeanFactory`**：IoC **容器根接口**（`getBean` 等）。**`FactoryBean`**：一种 **工厂 Bean**，`getObject()` 才是真正的 Bean；用于 **创建复杂对象**（如 MyBatis `MapperFactoryBean`）。`&` 前缀可拿 **FactoryBean 自身**。

---

## 二、Spring MVC 与 Web

### 8. `DispatcherServlet` 处理请求的大致流程？

**答：** **请求 → `DispatcherServlet` → `HandlerMapping` 找处理器（Controller 方法）→ `HandlerAdapter` 执行 → 参数解析（`HttpMessageConverter` 等）→ 调用方法 → 返回值处理（`ViewResolver` 或消息转换）→ 响应**。  
**异常：** `@ControllerAdvice` **全局异常处理** 拦截。  
**REST：** `@RestController` 少走视图解析，直接序列化 JSON。

---

### 9. Spring MVC 常用注解？

**答：** `@RequestMapping` 及其派生（`@GetMapping` 等）、**`@RequestParam` / `@PathVariable` / `@RequestBody` / `@RequestHeader`**、`@Valid` + Bean Validation、`@ResponseStatus` 等。**内容协商** 与 **`produces/consumes`** 控制 MIME。

---

### 10. 拦截器 `HandlerInterceptor` 与过滤器 `Filter` 区别？

**答：** **Filter** 在 **Servlet 容器** 层，**先于** DispatcherServlet；能做 **编码、跨域、鉴权前置** 等。**Interceptor** 在 **Spring MVC** 内，**能拿到 Handler 信息**，更贴近业务（登录态、审计、细粒度鉴权）。**执行顺序：** Filter chain → DispatcherServlet → Interceptor `preHandle` → Controller → `postHandle` → `afterCompletion`。

---

## 三、AOP

### 11. AOP 核心概念？

**答：** **切面（Aspect）**、**连接点（JoinPoint）**、**切点（Pointcut）**、**通知（Advice：前置/后置/环绕/异常/最终）**、**织入（Weaving）**。Spring 默认 **运行时动态代理**：**接口** 用 **JDK Proxy**，**无接口** 用 **CGLIB**（子类代理）。**同类自调用** 不走代理 → **环绕/事务** 可能失效。

---

### 12. `@Transactional` 不生效常见原因？

**答：** **非 public**、**自调用**、**异常类型不匹配**（默认只回滚 Runtime/Error，受检异常需 `rollbackFor`）、**数据库引擎不支持**（如 MyISAM）、**多数据源未配 TM**、**只读事务与传播行为误用**、**未被 Spring 管理** 的 Bean、**异步线程** 中事务上下文丢失等。

---

### 13. 事务传播行为 `PROPAGATION_*` 如何背？

**答：** 记 **最常用 3 个**：  
- **`REQUIRED`（默认）**：有则加入，无则新建。  
- **`REQUIRES_NEW`**：挂起当前，**新建独立事务**（审计、日志隔离）。  
- **`NESTED`**：**嵌套回滚点**（底层依赖 **保存点/JDBC**），与 `REQUIRES_NEW` 区别常被追问。  
其余 `SUPPORTS`、`NOT_SUPPORTED`、`MANDATORY`、`NEVER` 按语义记「要不要事务、有没有就抛错」。

---

### 14. 事务隔离级别与应用侧选择？

**答：** `READ_UNCOMMITTED` / `READ_COMMITTED` / `REPEATABLE_READ` / `SERIALIZABLE`。  
**MySQL InnoDB** 默认 **RR**（注：幻读在 InnoDB 下用 **GAP Lock** 等缓解，语义细节可深问）。  
**面经答法：** **读已提交** 更贴近很多 OLTP；**可重复读** 适合 **报表一致性读**；**串行化** 少见。**应用层** 仍需 **乐观锁 / 唯一约束** 处理并发更新。

---

## 四、Spring Boot：启动与自动配置

### 15. `SpringApplication.run` 做了什么（High level）？

**答：** 创建 **`ApplicationContext`**、刷新容器 **装载 Bean**、触发 **`ApplicationRunner`/`CommandLineRunner`**、启动 **嵌入式 Web 容器**（如 Tomcat on the classpath）、注册 **shutdown hook**。**外部化配置**、**日志系统** 初始化也在启动链路中。

---

### 16. 自动配置原理：`@SpringBootApplication` 里有什么？

**答：** 复合注解：**`@SpringBootConfiguration`**（本质 `@Configuration`）、**`@EnableAutoConfiguration`**、**`@ComponentScan`**。  
**`EnableAutoConfiguration`** 通过 **`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`**（Boot 3 起）或旧版 **`spring.factories`**（迁移期仍可能被提及）加载 **自动配置类**。配合 **`@ConditionalOnClass` / `@ConditionalOnMissingBean`** 等 **条件注解** 实现 **按需装配**。

---

### 17. `application.yml` 优先级、profile、多环境如何组织？

**答：** **配置优先级** 以官方文档为准（**命令行 > 环境变量 > jar 外置 > jar 内** 等，版本间有微调）。**`spring.profiles.active`** 激活 **dev/test/prod**；**`spring.config.import`** 引入 **Nacos/Consul** 等。**敏感信息** 倾向 **环境变量/密钥服务**，避免入库 Git。

---

### 18. Starter 的作用？自己写一个 Starter 要点？

**答：** **依赖聚合 + 自动配置**，开箱即用。**自定义：** `autoconfigure` 模块 + `META-INF` 里注册 AutoConfiguration + **完善的条件注解** + **配置属性 `@ConfigurationProperties`（推荐开启 `spring-boot-configuration-processor`）**。

---

## 五、Spring Boot 3 与生态升级

### 19. Spring Boot 3 / Spring 6 必提的三件事？

**答：**  
1. **`javax.*` → `jakarta.*`**（Tomcat、JPA、Servlet API 等全迁）。  
2. **最低 JDK 17**（生态对齐现代语言特性）。  
3. **观测：** **Micrometer / Micrometer Tracing** 取代旧 Sleuth 心智（具体 starter 以 BOM 为准）。

---

### 20. AOT 与 Native Image 在面试里怎么说？

**答：** **AOT（提前处理）**：构建期生成 **可预测的 Bean 元数据与反射提示**，减少启动时类扫描与配置解析，为 **GraalVM Native Image** 铺路。**Native Image**：**更快的启动与更小内存**，代价是 **构建慢、反射/动态代理需额外配置**、部分库 **兼容性** 需验证。**适用：** Serverless、CLI、边缘；**传统长运行 JVM** 仍常见。

---

### 21. 虚拟线程（Java 21）与 Spring Boot 如何配合？

**答：** **Tomcat/Undertow** 等可配置 **虚拟线程执行请求**，利点：**阻塞式代码**（JDBC、HTTP 客户端）在高并发下 **显著降低 OS 线程压力**。注意：**pinning**（在 `synchronized` 内阻塞 I/O）会削弱收益；**用 `ReentrantLock` 或重构**。**不要** 把虚拟线程当作「万能卡」，CPU 密集仍要靠 **算法与并行框架**。

---

## 六、Spring Cloud：体系与组件选型

### 22. Spring Cloud 与 Spring Boot 关系？

**答：** **Spring Boot** 是 **应用快速构造** 的基础；**Spring Cloud** 在 Boot 之上提供 **分布式系统的「一等公民」能力**（注册发现、配置、路由、熔断、链路、契约等），**版本需对齐 BOM（release train）**，避免 ** starters 混搭地狱**。

---

### 23. Nacos、Eureka、Consul 怎么对比（面试简版）？

**答：**  
- **Eureka（Netflix，维护热度下降）**：经典 AP 模型、**自助保护**、**客户端缓存**，**配置中心** 需另配。  
- **Consul**：**CP 强一致** 可选、**服务网格周边**、多数据中心；**健康检查**丰富。  
- **Nacos（国内面经高频）**：**注册 + 配置** 一体、**AP/CP 可切换（Naming）**、控制台友好；需理解 **长连接推送、集群脑裂、配置灰度** 等运维题。  
**选型：** 存量 Spring Cloud Netflix 迁移；新项目常 **Nacos / K8s Service** 二选一或并存。

---

### 24. Spring Cloud Config vs Nacos / Apollo？

**答：** **Config Server + Git**：**版本化、审计、回滚** 强；**实时推送** 能力弱，多需 **Bus（逐渐淡出心智）** 或 **Webhook**。**Nacos/Apollo**：**秒级推送、灰度、权限、审计 UI**；**缺点** 是需 **自建高可用集群**。**K8s** 场景也可能 **ConfigMap + Secret** 为主。

---

## 七、服务调用、负载均衡与容错

### 25. OpenFeign 是什么？为何优于裸 `RestTemplate`？

**答：** **声明式 HTTP 客户端**：接口 + 注解映射路由、参数、Header。**集成 LoadBalancer** 做 **服务发现后的负载均衡**。优点：**类型安全、可读性、统一拦截器（重试、日志、传递 Trace）**。**注意：** **超时、重试、幂等** 要成体系配置，避免 **雪崩式重试**。

---

### 26. 负载均衡：`@LoadBalanced` 背后机制？

**答：** Spring Cloud **客户端负载均衡**：从注册中心取 **实例列表**，**过滤器** 选择 **一个实例** 发起请求。**Ribbon（老）** 已被 **`spring-cloud-loadbalancer`** 取代为默认心智。

---

### 27. 熔断、限流、降级：Hystrix 凉了用什么？

**答：** **Hystrix 维护模式**。**Resilience4j**、**Sentinel** 为面经常客：**Resilience4j** 贴合 Spring/Reactive、函数式；**Sentinel** **控制台、热点参数限流、集群限流**强。要讲清：**熔断**（错误率/慢调用）、**舱壁**、**超时**、**重试+抖动**、**降级返回** 的组合。

---

### 28. 重试与幂等如何和服务间调用一起设计？

**答：** **GET/查询** 可适度重试；**POST 下单** 等非幂等需 **业务幂等键（Idempotency-Key）**、**Token 表** 或 **数据库唯一约束**。**重试** 配 **指数退避 + 最大次数**；与 **熔断** 联动避免 **重试风暴**。

---

## 八、网关、安全与配置

### 29. Gateway 与 Zuul 1.x 差异？

**答：** **Zuul 1**：Servlet **阻塞** 模型。**Spring Cloud Gateway**：**WebFlux（Netty）+ Route + Predicate + Filter**，**非阻塞** 在高并发下更有优势。**生产** 网关还要谈 **TLS 终结、WAF、Auth、限流、灰度路由**。

---

### 30. 网关层如何做灰度？

**答：** **基于 Header/Tag**（如 `version=canary`）**Predicate** 路由到 **灰度实例**；或 **注册中心元数据权重**；**配置中心动态下发** 路由表。**关键：** **链路标志透传**（Feign 拦截器、MQ Header），避免 **后端仍走默认负载**。

---

### 31. Spring Security / OAuth2 / JWT 微服务里常见链路？

**答：** **网关验签**（JWT）+ **细粒度授权在后端**；或 **Opaque Token + introspection**。**资源服务器** 校验 **scope/role**。**注意：** **时钟偏移、密钥轮换、Token 黑名单（或短 TTL + refresh）**。

---

## 九、可观测性、测试与部署

### 32. 链路追踪在 Boot 3 语境怎么说？

**答：** **Micrometer Observation + Tracing bridge**：生成 **Trace/Span**，导出 **OTLP/Jaeger/Zipkin**（依实现）。要会解释 **`traceId` 在日志 MDC 的关联**、**跨线程传递**、**跨进程 Propagation**。

---

### 33. Actuator 暴露哪些信息？生产注意事项？

**答：** **健康检查、指标、环境、线程 dump、heapdump（慎用）** 等。**生产必须：** **最小暴露、鉴权、网络隔离**；**敏感端点禁公网**。**K8s** 结合 **Liveness/Readiness**。

---

### 34. 本地与集成测试常用手段？

**答：** **`@SpringBootTest` + Testcontainers（MySQL/Kafka）**、**WireMock** 模拟下游、**契约测试（Spring Cloud Contract）**。区分 **纯单测** 与 **切片测试**（`@WebMvcTest`、`@DataJpaTest`）。

---

## 十、实战场景题

### 35. 超卖场景：Spring 事务 + 数据库行锁怎么讲？

**答：** **Service `@Transactional`** 内 **`UPDATE stock WHERE id=? AND stock>=n`**，看 **影响行数**；失败则 **回滚/业务异常**。**防重：** **订单幂等号**。**更大流量：** **缓存预热、分段库存、MQ 削峰、异步对账**；**分布式一致性** 见分布式事务专题。

---

### 36. 「慢接口拖垮线程池」如何排查与缓解？

**答：** **排查：** Arthas **profiler**、线程 dump、**指标（线程池队列长度）**、**Tracing 慢 span**。  
**缓解：** **超时熔断**、**隔离舱壁**、**异步化**、**缓存**、**限流**，前端 **降级文案**。

---

### 37. 配置动态刷新不生效？

**答：** **Scope**：`@RefreshScope` 对 **带 `@ConfigurationProperties` 的 Bean** 的心智；**同类 Bean 内部引用** 可能仍是 **旧代理**。**Nacos**：**dataId/group、命名空间** 是否一致；**监听器** 是否收到事件；**WebSocket 推送失败** 时 **是否回退轮询**。

---

## 十一、面经高频补充

### 38. Spring 与 Spring Boot 最大区别一句话？

**答：** **Spring** 是 **全栈编程与配置模型**；**Spring Boot** 是 **约定 + 自动配置 + 内嵌服务器 + 生产级 starter** 的 **工程化加速器**。

---

### 39. Spring MVC 与 Spring WebFlux 怎么选？

**答：** **多数团队以 MVC 为主**（生态、调试、人员结构）。**WebFlux** 适合 **高并发 I/O、网关、流式**；**JDBC 阻塞** 生态在 **全链路非阻塞** 上要谨慎评估 **R2DBC** 等。

---

### 40. Feign 超时默认值不清会怎样？

**答：** **下游抖动** → **线程堆积** → **连锁故障**。必须明确 **connect/read timeout**、**重试条件**、**熔断阈值**，并与 **线程池大小** 匹配。

---

### 41. K8s 时代还要注册中心吗？

**答：** **集群内** 常用 **Service + DNS**；**跨集群、多语言、灰度元数据、配置中心一体** 时仍可能要 **Nacos/Consul**。**面试答法：** **按组织复杂度与治理需求** 折中，而非非黑即白。

---

### 42. Spring Cloud Alibaba 与 Netflix 组件对照？

**答：** 典型心智：**Nacos** ↔ Eureka + Config；**Sentinel** ↔ Hystrix（部分）；**Seata** 管分布式事务；**RocketMQ Spring** 做消息。**版本兼容性** 查 **Spring Cloud Alibaba release notes**。

---

## 十二、自测清单

| 考点 | 一句话 |
|------|--------|
| IoC/DI | **容器管生命周期与装配** |
| 循环依赖 | **三级缓存、构造器不行** |
| 事务 | **自调用失效、传播、隔离、rollbackFor** |
| AOP | **代理、同类自调用坑** |
| Boot 启动 | **AutoConfiguration + 条件装配** |
| Boot 3 | **Jakarta、JDK17、观测换 Micrometer 心智** |
| Cloud | **注册、配置、RPC、网关、熔断限流、链路** |
| Feign | **声明式、负载均衡、超时重试幂等** |
| Gateway | **Route/Predicate/Filter、非阻塞** |
| 灰度 | **元数据/Header 路由 + 透传** |

---

*路径：`interview/spring/spring-interview.md`（含 **十一、面经高频补充**）*
