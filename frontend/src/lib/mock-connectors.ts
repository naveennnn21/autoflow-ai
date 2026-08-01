import type { Connector } from "@/types";

export const connectors: Connector[] = [
  {
    id: "slack", slug: "slack", name: "Slack", category: "Communication",
    description: "Send messages, post to channels, and react to workspace activity in real time.",
    logo: "slack", color: "#611f69", auth: "oauth2", scopes: ["chat:write", "channels:read", "users:read"],
    actions: [
      { id: "post_message", name: "Post Message", description: "Send a message to a channel", inputs: ["channel", "text"], outputs: ["ts"], kind: "write" },
      { id: "create_channel", name: "Create Channel", description: "Create a new channel", inputs: ["name"], outputs: ["channel_id"], kind: "write" },
      { id: "search_messages", name: "Search Messages", description: "Search workspace messages", inputs: ["query"], outputs: ["messages"], kind: "search" },
    ],
    triggers: [
      { id: "new_message", name: "New Message", description: "Triggers on new message", kind: "webhook" },
      { id: "mention", name: "Mention", description: "Triggers when the bot is mentioned", kind: "webhook" },
    ],
    rateLimit: "100 req/min", health: "healthy", rating: 4.9, installs: 12480, installed: true, verified: true, popular: true,
  },
  {
    id: "gmail", slug: "gmail", name: "Gmail", category: "Email",
    description: "Read, send, and organize emails with full Gmail API support.",
    logo: "mail", color: "#EA4335", auth: "oauth2", scopes: ["gmail.send", "gmail.readonly"],
    actions: [
      { id: "send_email", name: "Send Email", description: "Send a new email", inputs: ["to", "subject", "body"], outputs: ["message_id"], kind: "write" },
      { id: "search_emails", name: "Search Emails", description: "Search inbox", inputs: ["query"], outputs: ["emails"], kind: "search" },
    ],
    triggers: [
      { id: "new_email", name: "New Email", description: "Triggers on new email", kind: "webhook" },
      { id: "email_sent", name: "Email Sent", description: "Triggers when email sent", kind: "polling" },
    ],
    rateLimit: "250 req/min", health: "healthy", rating: 4.8, installs: 9864, installed: true, verified: true, popular: true,
  },
  {
    id: "github", slug: "github", name: "GitHub", category: "Developer",
    description: "Automate repos, issues, PRs, and CI/CD pipelines.",
    logo: "github", color: "#24292F", auth: "oauth2", scopes: ["repo", "workflow"],
    actions: [
      { id: "create_issue", name: "Create Issue", description: "Create a new issue", inputs: ["repo", "title", "body"], outputs: ["issue_number"], kind: "write" },
      { id: "create_pr", name: "Create PR", description: "Open a pull request", inputs: ["repo", "title", "head"], outputs: ["pr_number"], kind: "write" },
    ],
    triggers: [
      { id: "issue_opened", name: "Issue Opened", description: "Triggers on issue creation", kind: "webhook" },
      { id: "pr_merged", name: "PR Merged", description: "Triggers when PR merges", kind: "webhook" },
    ],
    rateLimit: "5000 req/hr", health: "healthy", rating: 4.9, installs: 8532, installed: true, verified: true, popular: true,
  },
  {
    id: "notion", slug: "notion", name: "Notion", category: "Productivity",
    description: "Create pages, databases, and comments across your workspace.",
    logo: "notion", color: "#111111", auth: "oauth2", scopes: ["read_content", "write_content"],
    actions: [
      { id: "create_page", name: "Create Page", description: "Create a new page", inputs: ["parent", "title", "content"], outputs: ["page_id"], kind: "write" },
      { id: "add_db_row", name: "Add DB Row", description: "Add row to database", inputs: ["database_id", "properties"], outputs: ["page_id"], kind: "write" },
    ],
    triggers: [
      { id: "page_created", name: "Page Created", description: "Triggers on page creation", kind: "polling" },
    ],
    rateLimit: "3 req/s", health: "healthy", rating: 4.7, installs: 7645, installed: false, verified: true,
  },
  {
    id: "stripe", slug: "stripe", name: "Stripe", category: "Payments",
    description: "Automate payments, subscriptions, invoices, and customers.",
    logo: "stripe", color: "#635BFF", auth: "api_key", scopes: ["charges", "customers", "subscriptions"],
    actions: [
      { id: "create_customer", name: "Create Customer", description: "Create a new customer", inputs: ["email", "name"], outputs: ["customer_id"], kind: "write" },
      { id: "create_charge", name: "Create Charge", description: "Charge a customer", inputs: ["customer_id", "amount"], outputs: ["charge_id"], kind: "write" },
    ],
    triggers: [
      { id: "invoice_paid", name: "Invoice Paid", description: "Triggers on invoice payment", kind: "webhook" },
      { id: "customer_created", name: "Customer Created", description: "Triggers on new customer", kind: "webhook" },
    ],
    rateLimit: "100 req/s", health: "healthy", rating: 4.8, installs: 6871, installed: false, verified: true, popular: true,
  },
  {
    id: "shopify", slug: "shopify", name: "Shopify", category: "E-commerce",
    description: "Manage products, orders, and inventory from your store.",
    logo: "shopping-bag", color: "#96BF48", auth: "oauth2", scopes: ["read_products", "write_orders"],
    actions: [
      { id: "create_product", name: "Create Product", description: "Create a new product", inputs: ["title", "price"], outputs: ["product_id"], kind: "write" },
      { id: "update_inventory", name: "Update Inventory", description: "Set inventory level", inputs: ["product_id", "quantity"], outputs: ["ok"], kind: "write" },
    ],
    triggers: [
      { id: "order_created", name: "Order Created", description: "Triggers on new order", kind: "webhook" },
    ],
    rateLimit: "40 req/s", health: "healthy", rating: 4.6, installs: 4520, installed: false,
  },
  {
    id: "discord", slug: "discord", name: "Discord", category: "Communication",
    description: "Send messages and manage servers and channels.",
    logo: "message-square", color: "#5865F2", auth: "bearer", scopes: ["messages.read", "guilds.write"],
    actions: [
      { id: "send_message", name: "Send Message", description: "Send message to channel", inputs: ["channel_id", "content"], outputs: ["message_id"], kind: "write" },
    ],
    triggers: [
      { id: "message_sent", name: "Message Sent", description: "Triggers on new message", kind: "webhook" },
    ],
    rateLimit: "50 req/s", health: "healthy", rating: 4.5, installs: 3890, installed: false,
  },
  {
    id: "google-drive", slug: "google-drive", name: "Google Drive", category: "Storage",
    description: "Upload, download, and organize files in Drive.",
    logo: "hard-drive", color: "#4285F4", auth: "oauth2", scopes: ["drive.file"],
    actions: [
      { id: "upload_file", name: "Upload File", description: "Upload a file", inputs: ["name", "content"], outputs: ["file_id"], kind: "upload" },
      { id: "list_files", name: "List Files", description: "List files in folder", inputs: ["folder_id"], outputs: ["files"], kind: "read" },
    ],
    triggers: [
      { id: "file_created", name: "File Created", description: "Triggers on new file", kind: "polling" },
    ],
    rateLimit: "100 req/s", health: "healthy", rating: 4.7, installs: 3210, installed: false,
  },
  {
    id: "airtable", slug: "airtable", name: "Airtable", category: "Database",
    description: "Sync records and bases with two-way automation.",
    logo: "table", color: "#F82B60", auth: "api_key", scopes: ["data.records"],
    actions: [
      { id: "create_record", name: "Create Record", description: "Add a record", inputs: ["base_id", "table", "fields"], outputs: ["record_id"], kind: "write" },
      { id: "update_record", name: "Update Record", description: "Update fields", inputs: ["record_id", "fields"], outputs: ["record_id"], kind: "write" },
    ],
    triggers: [
      { id: "record_created", name: "Record Created", description: "Triggers on new record", kind: "polling" },
    ],
    rateLimit: "5 req/s", health: "healthy", rating: 4.6, installs: 2984, installed: false,
  },
  {
    id: "linear", slug: "linear", name: "Linear", category: "Productivity",
    description: "Automate issues, cycles, and project tracking.",
    logo: "git-branch", color: "#5E6AD2", auth: "oauth2", scopes: ["issues:read", "issues:write"],
    actions: [
      { id: "create_issue", name: "Create Issue", description: "Create a new issue", inputs: ["team_id", "title"], outputs: ["issue_id"], kind: "write" },
    ],
    triggers: [
      { id: "issue_created", name: "Issue Created", description: "Triggers on new issue", kind: "webhook" },
    ],
    rateLimit: "100 req/min", health: "degraded", rating: 4.8, installs: 2104, installed: false,
  },
  {
    id: "postgres", slug: "postgres", name: "PostgreSQL", category: "Database",
    description: "Query and mutate tables with parameterized SQL.",
    logo: "database", color: "#336791", auth: "basic", scopes: ["read", "write"],
    actions: [
      { id: "run_query", name: "Run Query", description: "Execute a SQL query", inputs: ["sql", "params"], outputs: ["rows"], kind: "read" },
      { id: "insert_row", name: "Insert Row", description: "Insert into a table", inputs: ["table", "data"], outputs: ["id"], kind: "write" },
    ],
    triggers: [],
    rateLimit: "unlimited", health: "healthy", rating: 4.5, installs: 1874, installed: false,
  },
  {
    id: "hubspot", slug: "hubspot", name: "HubSpot", category: "CRM",
    description: "Sync contacts, deals, and pipelines across your CRM.",
    logo: "users", color: "#FF7A59", auth: "oauth2", scopes: ["crm.objects.contacts"],
    actions: [
      { id: "create_contact", name: "Create Contact", description: "Create a contact", inputs: ["email", "firstname"], outputs: ["contact_id"], kind: "write" },
    ],
    triggers: [
      { id: "contact_created", name: "Contact Created", description: "Triggers on new contact", kind: "webhook" },
    ],
    rateLimit: "100 req/s", health: "healthy", rating: 4.4, installs: 1532, installed: false,
  },
];
