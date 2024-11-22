Based on the provided software requirements specification, here is a detailed pseudocode for the core system components, focusing on clarity, modularity, and established design patterns.

## 1. System Components

### 1.1 Data Structures
```
// Define primary data structures

Class User {
    String userId
    String email
    String passwordHash
    Role role
    // Relationships
    List<PaymentLink> paymentLinks
    List<VirtualCard> virtualCards
    // Data validation rules
    validateEmail(email)
    validatePassword(password)
}

Class PaymentLink {
    String linkId
    String url
    Double amount
    User user
    // Data validation rules
    validateAmount(amount)
}

Class UsageData {
    String usageId
    User user
    Double unitsConsumed
    DateTime periodStart
    DateTime periodEnd
    // Data validation rules
    validateUnits(unitsConsumed)
}

Class VirtualCard {
    String cardId
    User user
    Double limit
    Boolean isActive
    // Data validation rules
    validateLimit(limit)
}

Enum Role {
    ADMIN, USER, FINANCE_MANAGER
}
```

### 1.2 Core Modules

```
// For each major component

Module PaymentLinkManager {
    // Module purpose and dependencies
    // This module manages the creation and lifecycle of payment links
    Dependencies: StripeAPI, Database

    // Public interfaces
    Function createPaymentLink(User user, Double amount): PaymentLink
    Function getPaymentLink(String linkId): PaymentLink
    Function listPaymentLinks(User user): List<PaymentLink>

    // Internal functions
    Private Function generatePaymentLinkUrl(Double amount): String
    Private Function storePaymentLink(PaymentLink link): Boolean

    // Error handling
    Handle StripeAPIError
    Handle InvalidAmountError
}

Module BillingManager {
    // Module purpose and dependencies
    // This module handles metered billing and usage data
    Dependencies: Database

    // Public interfaces
    Function recordUsage(User user, Double units): Boolean
    Function getBillingReport(User user): List<UsageData>

    // Internal functions
    Private Function calculateBilling(User user): Double

    // Error handling
    Handle DatabaseConnectionError
    Handle InvalidUsageError
}

Module VirtualCardManager {
    // Module purpose and dependencies
    // This module manages virtual card creation and usage
    Dependencies: PaymentProcessorAPI, Database

    // Public interfaces
    Function createVirtualCard(User user, Double limit): VirtualCard
    Function getVirtualCard(String cardId): VirtualCard
    Function listVirtualCards(User user): List<VirtualCard>

    // Internal functions
    Private Function initializeVirtualCard(Double limit): String
    Private Function storeVirtualCard(VirtualCard card): Boolean

    // Error handling
    Handle PaymentProcessorAPIError
    Handle InvalidCardLimitError
}
```

### 1.3 Algorithms

```
// Key algorithmic solutions

Algorithm GeneratePaymentLink
    Input: User user, Double amount
    Output: PaymentLink
    Steps:
        Validate amount using PaymentLink.validateAmount
        Generate URL using generatePaymentLinkUrl(amount)
        Create PaymentLink object
        Store in database with storePaymentLink(link)
        Return PaymentLink
    Edge cases: Handle amount = 0, amount < 0
    Performance: Optimized for low latency API calls

Algorithm RecordUsage
    Input: User user, Double units
    Output: Boolean success
    Steps:
        Validate units using UsageData.validateUnits
        Create UsageData object
        Store usage data in database
        Return success
    Edge cases: Handle units = 0, units < 0
    Performance: Batch processing for high volume data
```

## 2. Integration Points

```
// External system interfaces

Interface StripeAPI {
    Function createPaymentLink(Double amount): String
    Function retrievePaymentDetails(String linkId): PaymentDetails
    // API contracts
    // Data transformations as needed for integration
    // Error handling for API failures
    // Retry strategies with exponential backoff
}

Interface OpenAI {
    Function analyzeTransactionData(String data): AnalysisResult
    // API contracts
    // Data transformations for AI processing
    // Error handling for API failures
    // Retry strategies with exponential backoff
}
```

## 3. Control Flow

```
// Main process flows

ControlFlow MainProcess
    Initialize application
    Authenticate user using OAuth 2.0
    While user is logged in
        Display user dashboard
        If user selects "Create Payment Link"
            Execute GeneratePaymentLink
        If user selects "View Billing"
            Execute RecordUsage
        If user selects "Create Virtual Card"
            Execute VirtualCardManager.createVirtualCard
    On error, display user-friendly message
    On logout, cleanup user session
    Shutdown application gracefully

// Initialization sequence
Initialize database connections
Initialize API clients (StripeAPI, OpenAI)
Load configuration settings

// State management
Maintain user session state
Track current active processes

// Error recovery
Implement retry logic for transient errors
Log errors for diagnostic purposes

// Cleanup procedures
Close database connections
Release API client resources
Clear temporary data
```

This pseudocode provides a modular and clear representation of the system components, integration points, and control flow, adhering to the software requirements specification.