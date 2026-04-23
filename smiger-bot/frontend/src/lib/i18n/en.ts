const en = {
  // Landing page
  landing: {
    title: "Smiger Guitar Expert",
    subtitle:
      "Your 24/7 AI-powered pre-sales consultant for Smiger guitars. Ask about our products, get personalized recommendations, and request quotes — all in real time.",
    feature1Title: "Product Expertise",
    feature1Desc:
      "Deep knowledge of Smiger's full guitar line — acoustic, electric, bass, ukulele and accessories.",
    feature2Title: "Instant Quotes",
    feature2Desc:
      "Share your needs and receive detailed catalog and pricing from our team within 24 hours.",
    feature3Title: "24/7 Available",
    feature3Desc:
      "No timezone barriers. Get professional assistance any time, from anywhere in the world.",
    chatHint: "Click the chat icon in the bottom-right corner to start a conversation →",
  },

  // Chat widget
  chat: {
    headerTitle: "Smiger Guitar Expert",
    headerStatus: "Online — typically replies instantly",
    humanMode: "Sales representative connected",
    greeting:
      "Hi there! 👋 Welcome to Smiger Guitars. I'm your AI product specialist.\n\nWhether you're looking for acoustic guitars, electric guitars, bass, or ukuleles — I'm here to help you find the perfect instruments for your business.\n\nWhat are you looking for today?",
    inputPlaceholder: "Type your message...",
    submitError: "Failed to submit. Please try again.",
    leadThanks:
      "Thank you for sharing your details! 🎸 Our team will review your requirements and send you a personalized catalog and quote within 24 hours. In the meantime, feel free to keep asking me anything!",
    handoffNotice:
      "Thank you for your purchase interest! A sales representative will assist you shortly. Please fill in your contact details so we can follow up with you.",
    salesConnected: "A sales representative has joined the conversation.",
    handoffResolved: "The live support session has ended. The AI assistant is back to help you.",
  },

  // Lead form
  lead: {
    title: "Get Your Personalized Quote",
    subtitle:
      "Leave your details and our team will send you a detailed catalog and pricing within 24 hours.",
    name: "Your Name",
    company: "Company",
    email: "Email *",
    phone: "Phone",
    country: "Country",
    requirement: "Tell us about your needs (product type, quantity, etc.)",
    submit: "Get My Quote",
    submitting: "Submitting...",
  },

  // Admin
  admin: {
    brand: "Smiger AI-OS",
    signOut: "Sign Out",
    dashboard: "Dashboard",
    handoff: "Handoff",
    knowledgeBase: "Knowledge Base",
    conversations: "Conversations",
    leads: "Leads",
    faq: "FAQ",
    csData: "CS Data",
    settings: "API Settings",
  },

  // Admin - Login
  login: {
    title: "Smiger AI-OS Admin",
    subtitle: "Sign in to manage your AI assistant",
    username: "Username",
    password: "Password",
    signIn: "Sign In",
    signingIn: "Signing in...",
    error: "Invalid username or password",
  },

  // Admin - Dashboard
  dashboardPage: {
    title: "Dashboard",
    loading: "Loading dashboard...",
    conversations: "Conversations",
    messages: "Messages",
    leadsCaptured: "Leads Captured",
    knowledgeDocs: "Knowledge Docs",
    today: "today",
  },

  // Admin - Knowledge
  knowledgePage: {
    title: "Knowledge Base",
    upload: "Upload Document",
    uploading: "Uploading...",
    description:
      "Upload product documents, FAQs, training materials, and sales scripts to power the AI assistant's knowledge.",
    thFile: "File",
    thType: "Type",
    thSize: "Size",
    thChunks: "Chunks",
    thStatus: "Status",
    thUploaded: "Uploaded",
    thAction: "Action",
    empty: "No documents uploaded yet.",
    deleteConfirm: (name: string) =>
      `Delete "${name}"? This will remove all its chunks from the knowledge base.`,
    statusReady: "Ready",
    statusError: "Error",
    statusProcessing: "Processing",
  },

  // Admin - Conversations
  conversationsPage: {
    title: "Conversations",
    empty: "No conversations yet.",
    noMessages: "No messages in this conversation.",
    selectHint: "Select a conversation to view",
    loading: "Loading messages...",
    turns: "turns",
  },

  // Admin - Leads
  leadsPage: {
    title: "Leads",
    export: "Export CSV",
    thName: "Name",
    thCompany: "Company",
    thEmail: "Email",
    thPhone: "Phone",
    thCountry: "Country",
    thRequirement: "Requirement",
    thDate: "Date",
    empty: "No leads captured yet.",
  },

  settingsPage: {
    title: "API Settings",
    llmSection: "LLM (Chat Completions)",
    embeddingSection: "Embedding Service",
    apiKey: "API Key",
    baseUrl: "Base URL",
    model: "Model",
    embeddingUrl: "Embedding URL",
    easyllmId: "EasyLLM ID",
    dimensions: "Dimensions",
    save: "Save Settings",
    saving: "Saving...",
    test: "Test Connection",
    testing: "Testing...",
    saved: "Settings saved successfully",
    connected: "Connected",
    failed: "Connection failed",
    whatsappSection: "WhatsApp Channel",
    whatsappAdminPhone: "Admin WhatsApp Number",
    whatsappTemplate: "Template Name (optional)",
    whatsappWebhookHint: "Configure this URL as the Webhook callback in Meta Developer Portal",
  },

  csPage: {
    title: "Customer Service Data",
    import: "Import JSON",
    importing: "Importing...",
    addRecord: "Add Record",
    stats: "Statistics",
    total: "Total Records",
    open: "Open",
    resolved: "Resolved",
    channels: "Channels",
    thCustomer: "Customer",
    thEmail: "Email",
    thChannel: "Channel",
    thSubject: "Subject",
    thAgent: "Agent",
    thStatus: "Status",
    thDate: "Date",
    empty: "No customer service records yet.",
  },

  faqPage: {
    title: "FAQ Management",
    addEntry: "Add FAQ",
    import: "Import File",
    importing: "Importing...",
    syncKnowledge: "Sync to KB",
    syncing: "Syncing...",
    syncSuccess: "Synced {entries} entries ({chunks} chunks) to knowledge base",
    search: "Search questions/answers...",
    allCategories: "All Categories",
    thQuestion: "Question",
    thAnswer: "Answer",
    thCategory: "Category",
    thTags: "Tags",
    thAction: "Action",
    empty: "No FAQ entries yet.",
    deleteConfirm: (q: string) => `Delete FAQ "${q}"?`,
    formTitle: "FAQ Entry",
    questionCn: "Question (CN)",
    questionEn: "Question (EN)",
    answerCn: "Answer (CN)",
    answerEn: "Answer (EN)",
    category: "Category",
    tags: "Tags (comma separated)",
    save: "Save",
    cancel: "Cancel",
    categories: {
      general: "General",
      pricing: "Pricing",
      moq: "MOQ",
      delivery: "Delivery",
      customization: "Customization",
      logistics: "Logistics",
      country_preferences: "Country Preferences",
    },
  },

  handoffPage: {
    title: "Handoff",
    empty: "No handoff requests",
    pending: "Pending",
    active: "Active",
    selectHint: "Select a conversation to start live support",
    accept: "Accept",
    resolve: "End Session",
    replyPlaceholder: "Type your reply... (Enter to send)",
    pendingHint: "This customer has purchase intent. Click \"Accept\" to start live support.",
  },

  langSwitch: "中文",
};

type DeepStringify<T> = {
  [K in keyof T]: T[K] extends (...args: infer A) => infer R
    ? (...args: A) => R
    : T[K] extends object
      ? DeepStringify<T[K]>
      : string;
};

export type Locale = DeepStringify<typeof en>;
export default en;
