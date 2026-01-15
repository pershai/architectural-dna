; Tree-sitter SCM Query for C# Attribute Detection
; Used for architectural role identification and dependency injection mapping

; ============================================================================
; ATTRIBUTE DETECTION
; ============================================================================

; Capture all attribute declarations
; Example: [ApiController], [Route("api/[controller]")]
(attribute
  name: (identifier) @attribute.name
  (attribute_argument_list
    (attribute_argument
      (_) @attribute.argument)*)?
) @attribute.full

; Capture attribute lists (multiple attributes)
; Example: [ApiController, Route("api/users")]
(attribute_list
  (attribute) @attribute.item
) @attribute.list

; ============================================================================
; CONTROLLER DETECTION
; ============================================================================

; Classes with [ApiController] attribute
(class_declaration
  (attribute_list
    (attribute
      name: (identifier) @controller.attribute
      (#match? @controller.attribute "^(ApiController|Controller)$")))
  name: (identifier) @controller.name
  body: (declaration_list) @controller.body
) @controller.class

; Controller base class inheritance
(class_declaration
  name: (identifier) @controller.name
  (base_list
    (simple_base_type
      (identifier) @controller.base
      (#match? @controller.base "^.*Controller$")))
) @controller.inherited

; ============================================================================
; DEPENDENCY INJECTION REGISTRATION
; ============================================================================

; Generic DI registration: services.AddTransient<IService, ServiceImpl>()
(invocation_expression
  (member_access_expression
    (identifier) @di.services_variable
    (identifier) @di.method
    (#match? @di.method "^Add(Transient|Scoped|Singleton)$"))
  (type_argument_list
    (type_argument
      (identifier) @di.interface)
    (type_argument
      (identifier) @di.implementation))?
) @di.registration

; DI registration with typeof: services.AddTransient(typeof(IService), typeof(ServiceImpl))
(invocation_expression
  (member_access_expression
    name: (identifier) @di.method
    (#match? @di.method "^Add(Transient|Scoped|Singleton)$"))
  (argument_list
    (argument
      (invocation_expression
        (identifier) @typeof1
        (#eq? @typeof1 "typeof")))
    (argument
      (invocation_expression
        (identifier) @typeof2
        (#eq? @typeof2 "typeof"))))?
) @di.typeof_registration

; ============================================================================
; REPOSITORY PATTERN DETECTION
; ============================================================================

; Interface declarations with "Repository" in name
(interface_declaration
  name: (identifier) @repository.interface
  (#match? @repository.interface "^I.*Repository$")
) @repository.interface_decl

; Classes implementing repository interfaces
(class_declaration
  name: (identifier) @repository.class
  (#match? @repository.class "^.*Repository$")
  (base_list
    (simple_base_type
      (identifier) @repository.base_interface))?
) @repository.class_decl

; ============================================================================
; MEDIATR PATTERN DETECTION
; ============================================================================

; MediatR Handler detection: IRequestHandler<TRequest, TResponse>
(class_declaration
  name: (identifier) @handler.name
  (base_list
    (simple_base_type
      (generic_name
        (identifier) @handler.interface
        (#match? @handler.interface "^IRequestHandler$"))))?
) @handler.class

; MediatR IMediator injection in constructors
(constructor_declaration
  (parameter_list
    (parameter
      type: (identifier) @mediator.type
      (#eq? @mediator.type "IMediator")
      name: (identifier) @mediator.param))
) @mediator.injection

; ============================================================================
; DOMAIN ENTITY DETECTION
; ============================================================================

; Classes with [Entity] or [DomainEntity] attributes
(class_declaration
  (attribute_list
    (attribute
      name: (identifier) @entity.attribute
      (#match? @entity.attribute "^(Entity|DomainEntity|Aggregate)$")))
  name: (identifier) @entity.name
) @entity.class

; Value Objects (marked with attribute)
(class_declaration
  (attribute_list
    (attribute
      name: (identifier) @valueobject.attribute
      (#match? @valueobject.attribute "^ValueObject$")))
  name: (identifier) @valueobject.name
) @valueobject.class

; Record types (often used for Value Objects in C# 9+)
(record_declaration
  name: (identifier) @record.name
) @record.decl

; ============================================================================
; ASYNC SAFETY DETECTION
; ============================================================================

; Detect .Result usage (async-over-sync anti-pattern)
(member_access_expression
  (identifier)
  (identifier) @async.result
  (#eq? @async.result "Result")
) @async.blocking_result

; Detect .Wait() usage
(invocation_expression
  (member_access_expression
    name: (identifier) @async.wait
    (#eq? @async.wait "Wait"))
) @async.blocking_wait

; Detect .GetAwaiter().GetResult()
(invocation_expression
  (member_access_expression
    (invocation_expression
      (member_access_expression
        name: (identifier) @async.getawaiter
        (#eq? @async.getawaiter "GetAwaiter")))
    (identifier) @async.getresult
    (#eq? @async.getresult "GetResult"))
) @async.blocking_getresult

; ============================================================================
; SQL ACCESS DETECTION
; ============================================================================

; Using directives for SQL libraries
(using_directive
  (qualified_name) @sql.namespace
  (#match? @sql.namespace "^(Microsoft\\.Data\\.SqlClient|System\\.Data\\.SqlClient|Dapper)")
) @sql.using

; SqlConnection instantiation
(object_creation_expression
  (identifier) @sql.connection
  (#match? @sql.connection "^SqlConnection$")
) @sql.connection_creation

; ============================================================================
; PARTIAL CLASS DETECTION
; ============================================================================

; Partial class declarations
(class_declaration
  (modifier) @partial.modifier
  (#eq? @partial.modifier "partial")
  name: (identifier) @partial.class_name
) @partial.class

; ============================================================================
; COMPLEXITY INDICATORS
; ============================================================================

; Method declarations (for counting)
(method_declaration
  name: (identifier) @method.name
) @method.decl

; Property declarations (for counting)
(property_declaration
  name: (identifier) @property.name
) @property.decl

; Field declarations (for counting)
(field_declaration
  (variable_declaration
    (variable_declarator
      (identifier) @field.name))
) @field.decl

; If statements (for cyclomatic complexity)
(if_statement) @complexity.if

; Switch statements
(switch_statement) @complexity.switch

; Loop statements
(while_statement) @complexity.while
(for_statement) @complexity.for
(foreach_statement) @complexity.foreach

; Conditional expressions (ternary operator)
(conditional_expression) @complexity.ternary

; Logical operators (for complexity)
(binary_expression
  (identifier)
  operator: (string) @complexity.operator
  (#match? @complexity.operator "^(&&|\\|\\|)$")
) @complexity.logical
