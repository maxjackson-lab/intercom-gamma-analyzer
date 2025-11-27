"""
Taxonomy Configuration for Intercom Analysis Tool.
Defines the 13 primary categories and 100+ subcategories for analysis.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import yaml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class Subcategory:
    """Represents a subcategory within a primary category."""
    name: str
    description: str
    keywords: List[str]
    confidence_threshold: float = 0.8


@dataclass
class Category:
    """Represents a primary category in the taxonomy."""
    name: str
    description: str
    subcategories: List[Subcategory]
    keywords: List[str]
    confidence_threshold: float = 0.7


class TaxonomyManager:
    """Manages the taxonomy configuration and mapping."""
    
    def __init__(self, taxonomy_file: Optional[str] = None):
        if taxonomy_file:
            self.taxonomy_file = Path(taxonomy_file)
        else:
            # Use absolute path from module location to work in any working directory
            module_dir = Path(__file__).parent
            self.taxonomy_file = module_dir / "taxonomy.yaml"
        
        self.categories: Dict[str, Category] = {}
        self._load_taxonomy()
    
    def _load_taxonomy(self):
        """Load taxonomy from YAML file or create default."""
        if self.taxonomy_file.exists():
            self._load_from_yaml()
        else:
            logging.warning(f"Taxonomy file not found at {self.taxonomy_file}, using default taxonomy")
            self._create_default_taxonomy()
            # Don't save to YAML if file doesn't exist - might be deployment environment
            # self._save_to_yaml()
    
    def _validate_keywords_encoding(self, keywords: List[str], context: str) -> List[str]:
        """
        Validate that keywords are properly encoded UTF-8 strings.
        Logs warnings for potentially problematic characters.
        """
        validated = []
        for kw in keywords:
            if not isinstance(kw, str):
                logger.warning(f"Skipping non-string keyword in {context}: {kw}")
                continue
                
            # Ensure it's proper UTF-8 (Python 3 strings are unicode by default, but good to check valid chars)
            try:
                kw.encode('utf-8')
                validated.append(kw)
            except UnicodeEncodeError:
                logger.warning(f"Invalid encoding for keyword in {context}: {kw}")
        return validated

    def _create_default_taxonomy(self):
        """Create the default Gamma taxonomy."""
        
        # Helper to validate list of keywords inline
        def v(keywords, context):
            return self._validate_keywords_encoding(keywords, context)

        self.categories = {
            "Abuse": Category(
                name="Abuse",
                description="Reports of harmful behavior, DMCA, malicious links",
                keywords=v(["abuse", "spam", "malicious", "dmca", "harassment", "inappropriate"], "Abuse"),
                subcategories=[
                    Subcategory("Spam", "Spam messages or content", v(["spam", "unsolicited", "promotional"], "Abuse.Spam")),
                    Subcategory("Malicious Links", "Suspicious or harmful links", v(["malicious", "virus", "phishing", "suspicious link"], "Abuse.MaliciousLinks")),
                    Subcategory("DMCA", "Copyright infringement reports", v(["dmca", "copyright", "infringement"], "Abuse.DMCA")),
                    Subcategory("Harassment", "Harassment or bullying", v(["harassment", "bullying", "threat", "intimidation"], "Abuse.Harassment")),
                    Subcategory("Inappropriate Content", "Inappropriate or offensive content", v(["inappropriate", "offensive", "explicit"], "Abuse.Inappropriate")),
                    Subcategory("Account Takeover", "Suspected account compromise", v(["hacked", "compromised", "unauthorized access"], "Abuse.AccountTakeover")),
                    Subcategory("Fake Account", "Suspected fake or impersonation", v(["fake", "impersonation", "identity theft"], "Abuse.FakeAccount")),
                    Subcategory("Report User", "User reporting another user", v(["report user", "block user", "user complaint"], "Abuse.ReportUser")),
                    Subcategory("Other Abuse", "Other abuse-related issues", v(["abuse", "violation", "policy violation"], "Abuse.Other"))
                ]
            ),
            
            "Account": Category(
                name="Account",
                description="Account access, settings, credits, email changes",
                keywords=v([
                    # English - Core terms
                    "account", "login", "password", "email", "settings", "credits",
                    
                    # English - Email operations (from 1000 conversation analysis)
                    "change email", "current email address", "add new email", 
                    "email address", "change the email", "update email",
                    
                    # English - Password operations
                    "reset password", "forgot password", "can't login", "unable to login",
                    "can't access", "unable to get into", "access account",
                    
                    # English - Account management
                    "delete account", "close account", "account deletion",
                    "domain", "company name", "team name",
                    
                    # English - Access issues
                    "locked out", "can't sign in", "unable to access",
                    
                    # Spanish (10.2% of conversations)
                    "cambiar correo", "contraseña", "cuenta", "acceso", "dominio",
                    "correo electrónico", "iniciar sesión", "no puedo acceder",
                    
                    # Portuguese (9.5% of conversations)
                    "mudar email", "senha", "conta", "acesso", "domínio",
                    "endereço de email", "não consigo acessar", "redefinir senha",
                    
                    # French (6.5% of conversations)
                    "changer email", "mot de passe", "compte", "domaine",
                    "adresse email", "réinitialiser mot de passe", "accès",
                    
                    # German (3.0% of conversations)
                    "E-Mail ändern", "Passwort", "Konto", "Domäne",
                    "E-Mail-Adresse", "Passwort zurücksetzen", "Zugriff",
                    
                    # Italian (3.5% of conversations)
                    "cambiare email", "password", "account", "accesso",
                    "indirizzo email", "reimpostare password", "dominio",

                    # Russian (5.0% of conversations) - Validated UTF-8
                    "аккаунт", "вход", "пароль", "доступ", "почта",
                    "сброс пароля", "войти",

                    # Korean (9.0% of conversations) - Validated UTF-8
                    "계정", "로그인", "비밀번호", "접속", "이메일",
                    "비번", "가입"
                ], "Account"),
                subcategories=[
                    Subcategory("Login Issues", "Problems logging in", v(["login", "sign in", "authentication", "password"], "Account.Login")),
                    Subcategory("Email Change", "Request to change email address", v(["email change", "update email", "new email"], "Account.EmailChange")),
                    Subcategory("Password Reset", "Password reset requests", v(["password reset", "forgot password", "reset password"], "Account.PasswordReset")),
                    Subcategory("Account Settings", "Account configuration changes", v(["settings", "preferences", "profile", "account settings"], "Account.Settings")),
                    Subcategory("Credits", "Credit-related questions", v(["credits", "balance", "usage", "billing credits"], "Account.Credits")),
                    Subcategory("Account Deletion", "Request to delete account", v(["delete account", "close account", "remove account"], "Account.Deletion")),
                    Subcategory("Two-Factor Auth", "2FA setup or issues", v(["2fa", "two factor", "authenticator", "security"], "Account.2FA")),
                    Subcategory("Account Access", "General account access issues", v(["access", "permissions", "locked out"], "Account.Access")),
                    Subcategory("Profile Update", "Profile information updates", v(["profile", "name change", "update profile"], "Account.Profile")),
                    Subcategory("Account Verification", "Account verification issues", v(["verification", "verify", "unverified"], "Account.Verification")),
                    Subcategory("Account Merge", "Merging multiple accounts", v(["merge", "combine", "duplicate account"], "Account.Merge")),
                    Subcategory("Other Account", "Other account-related issues", v(["account", "user", "member"], "Account.Other"))
                ]
            ),
            
            "Billing": Category(
                name="Billing",
                description="Refunds, invoices, subscriptions, payment methods",
                keywords=v([
                    # English - Core terms (validated by 651 billing conversations)
                    "billing", "payment", "invoice", "refund", "subscription", "credit card",
                    
                    # English - Refund operations (482 refund conversations analyzed)
                    "cancel", "cancelled", "charged", "charge", "want refund",
                    "charged twice", "unexpected charge", "return payment",
                    "cancel subscription", "not interested",
                    
                    # English - Invoice/receipt terms (184 invoice conversations)
                    "receipt", "invoice number", "receipt from", "billing statement",
                    
                    # English - Payment issues
                    "payment failed", "declined", "payment error",
                    
                    # English - Credits/balance (132 credits conversations)
                    "credits", "credit", "account balance", "balance",
                    
                    # English - Common phrases (from real data)
                    "from gamma", "gamma support", "subscription plan",
                    
                    # Portuguese (9.5% of conversations - 63 from Oct+Nov combined dataset)
                    "reembolso",        # refund
                    "cancelar",         # cancel
                    "cobrança",         # charge/billing
                    "estorno",          # refund/chargeback
                    "pagamento",        # payment
                    "assinatura",       # subscription
                    "fatura",           # invoice
                    "cartão de crédito", # credit card
                    "cartão",           # card (shortened - NEW from 2000 convs)
                    "recibo",           # receipt
                    "cobrança indevida", # unexpected charge
                    "valor",            # value/amount (NEW from 2000 convs)
                    "cancelamento",     # cancellation (NEW from 2000 convs)
                    "plano",            # plan (NEW from 2000 convs)
                    "quero"             # I want (NEW from 2000 convs)
                    
                    # Spanish (10.2% of conversations - 63 from Oct+Nov combined dataset)
                    "reembolso",        # refund
                    "cancelar",         # cancel
                    "factura",          # invoice
                    "pago", "pagado",   # payment, paid
                    "suscripción",      # subscription
                    "cargo",            # charge
                    "tarjeta de crédito", # credit card
                    "recibo",           # receipt
                    "cobro inesperado", # unexpected charge
                    "quiero",           # I want (NEW from 2000 convs)
                    "anual",            # annual (NEW from 2000 convs)
                    "cuenta",           # account (NEW from 2000 convs)
                    "necesito",         # I need (NEW from 2000 convs)
                    "plan",             # plan (NEW from 2000 convs)
                    "datos"             # data (NEW from 2000 convs)
                    
                    # French (6.5% of conversations - 65 French speakers)
                    "remboursement",    # refund
                    "annuler",          # cancel
                    "paiement",         # payment
                    "abonnement",       # subscription
                    "facture",          # invoice
                    "carte de crédit",  # credit card
                    "reçu",             # receipt
                    "frais inattendus", # unexpected charge
                    
                    # German (3.0% of conversations - 17 from Oct+Nov combined dataset)
                    "Rückerstattung",   # refund
                    "Rechnung",         # invoice
                    "Zahlung",          # payment
                    "Abbuchung",        # debit/charge
                    "Abonnement",       # subscription
                    "Kreditkarte",      # credit card
                    "Quittung",         # receipt
                    "stornieren",       # cancel
                    "nicht",            # not (NEW from 2000 convs - in "nicht autorisiert")
                    "habe",             # have (NEW from 2000 convs)
                    "mein",             # my (NEW from 2000 convs)
                    "lösen",            # solve (NEW from 2000 convs)
                    "unterstützung",    # support (NEW from 2000 convs)
                    "problem",          # problem (NEW from 2000 convs)
                    "kann"              # can (NEW from 2000 convs)
                    
                    # Italian (3.5% of conversations - 19 from Oct+Nov combined dataset)
                    "rimborso",         # refund
                    "cancellare",       # cancel
                    "abbonamento",      # subscription
                    "fattura",          # invoice
                    "pagamento",        # payment
                    "annuale",          # annual (NEW from 2000 convs)
                    "mensile",          # monthly (NEW from 2000 convs)
                    "piano",            # plan (NEW from 2000 convs)
                    "carta di credito", # credit card
                    "ricevuta",         # receipt
                    "addebito",         # charge
                    "salve",            # hello/greetings (NEW from 2000 convs)

                    # Russian (5.0% of conversations)
                    "оплата", "счет", "подписка", "возврат", "отмена",
                    "деньги", "тариф", "карта",

                    # Korean (9.0% of conversations)
                    "결제", "청구", "구독", "환불", "취소",
                    "요금", "카드", "영수증"
                ], "Billing"),
                subcategories=[
                    Subcategory("Refund", "Refund requests", v(["refund", "money back", "cancel payment"], "Billing.Refund")),
                    Subcategory("Subscription", "Subscription management", v(["subscription", "plan", "upgrade", "downgrade"], "Billing.Subscription")),
                    Subcategory("Invoice", "Invoice questions", v(["invoice", "receipt", "billing statement"], "Billing.Invoice")),
                    Subcategory("Payment Method", "Payment method updates", v(["payment method", "credit card", "billing info"], "Billing.PaymentMethod")),
                    Subcategory("Billing Info", "Billing information changes", v(["billing address", "tax info", "billing details"], "Billing.Info")),
                    Subcategory("Pricing", "Pricing questions", v(["price", "cost", "pricing", "how much"], "Billing.Pricing")),
                    Subcategory("Discount", "Discount requests", v(["discount", "coupon", "promo", "deal"], "Billing.Discount")),
                    Subcategory("Credit", "Account credits", v(["credit", "balance", "account credit"], "Billing.Credit")),
                    Subcategory("Failed Payment", "Payment failures", v(["failed payment", "declined", "payment error"], "Billing.Failed")),
                    Subcategory("Billing Cycle", "Billing cycle questions", v(["billing cycle", "renewal", "auto-renew"], "Billing.Cycle")),
                    Subcategory("Tax", "Tax-related questions", v(["tax", "vat", "taxes", "tax exempt"], "Billing.Tax")),
                    Subcategory("Currency", "Currency conversion", v(["currency", "exchange rate", "usd", "eur"], "Billing.Currency")),
                    Subcategory("Enterprise Billing", "Enterprise billing", v(["enterprise", "volume", "custom pricing"], "Billing.Enterprise")),
                    Subcategory("Trial", "Trial period questions", v(["trial", "free trial", "trial period"], "Billing.Trial")),
                    Subcategory("Cancellation", "Subscription cancellation", v(["cancel", "cancellation", "stop subscription"], "Billing.Cancellation")),
                    Subcategory("Reactivation", "Account reactivation", v(["reactivate", "restore", "reactivation"], "Billing.Reactivation")),
                    Subcategory("Proration", "Prorated billing", v(["proration", "prorated", "partial refund"], "Billing.Proration")),
                    Subcategory("Billing Dispute", "Billing disputes", v(["dispute", "chargeback", "billing error"], "Billing.Dispute")),
                    Subcategory("Payment History", "Payment history requests", v(["payment history", "transactions", "billing history"], "Billing.History")),
                    Subcategory("Billing Contact", "Billing contact changes", v(["billing contact", "account manager"], "Billing.Contact")),
                    Subcategory("Invoice Customization", "Custom invoice requests", v(["custom invoice", "invoice format"], "Billing.InvoiceCustom")),
                    Subcategory("Billing Export", "Billing data export", v(["export billing", "billing data", "financial report"], "Billing.Export")),
                    Subcategory("Multi-Currency", "Multi-currency billing", v(["multi-currency", "currency conversion"], "Billing.MultiCurrency")),
                    Subcategory("Billing Integration", "Billing system integration", v(["billing integration", "api billing"], "Billing.Integration")),
                    Subcategory("Billing Automation", "Automated billing", v(["automated billing", "auto-billing"], "Billing.Automation")),
                    Subcategory("Billing Analytics", "Billing analytics", v(["billing analytics", "usage analytics"], "Billing.Analytics")),
                    Subcategory("Billing Compliance", "Billing compliance", v(["compliance", "audit", "billing compliance"], "Billing.Compliance")),
                    Subcategory("Billing Migration", "Billing system migration", v(["migration", "billing migration"], "Billing.Migration")),
                    Subcategory("Other Billing", "Other billing issues", v(["billing", "payment", "financial"], "Billing.Other"))
                ]
            ),
            
            "Bug": Category(
                name="Bug",
                description="Product bugs, errors, functionality issues",
                keywords=v([
                    # English - Core error terms
                    "bug", "error", "broken", "not working", "issue", "problem",
                    
                    # English - Functionality issues (84 bug conversations analyzed)
                    "doesn't work", "won't work", "can't", "cannot", "unable",
                    "failed", "fails", "failing", "not loading", "won't load",
                    
                    # English - Specific issues (from real data)
                    "error message", "crashed", "crash", "stuck", "frozen",
                    "slow", "laggy", "glitch", "malfunction",
                    
                    # English - Action failures
                    "can't save", "won't export", "not generating", "won't publish",
                    "can't load", "won't open", "not responding",
                    
                    # Spanish (10.2% of conversations)
                    "no funciona", "error", "roto", "problema", "fallo",
                    "no se carga", "no puede", "no puedo",
                    
                    # Portuguese (9.5% of conversations)
                    "não funciona", "erro", "quebrado", "problema", "falha",
                    "não carrega", "não consigo", "não pode",
                    
                    # French (6.5% of conversations)
                    "ne fonctionne pas", "erreur", "cassé", "problème",
                    "ne charge pas", "ne peut pas",
                    
                    # German (3.0% of conversations)
                    "funktioniert nicht", "Fehler", "kaputt", "Problem",
                    "lädt nicht", "kann nicht",
                    
                    # Italian (3.5% of conversations)
                    "non funziona", "errore", "rotto", "problema",
                    "non carica", "non posso", "non può",

                    # Russian (5.0% of conversations)
                    "ошибка", "не работает", "баг", "проблема",
                    "сломалось", "зависло",

                    # Korean (9.0% of conversations)
                    "오류", "버그", "문제", "안됨", "안돼요",
                    "작동 안함", "에러"
                ], "Bug"),
                subcategories=[
                    Subcategory("Export", "Export functionality bugs", v(["export", "ppt", "pdf", "slides", "download"], "Bug.Export")),
                    Subcategory("Account", "Account-related bugs", v(["account bug", "login bug", "profile bug"], "Bug.Account")),
                    Subcategory("Agent", "AI agent bugs", v(["agent bug", "fin bug", "ai bug", "bot bug"], "Bug.Agent")),
                    Subcategory("API", "API-related bugs", v(["api bug", "api error", "integration bug"], "Bug.API")),
                    Subcategory("Authentication", "Authentication bugs", v(["auth bug", "login bug", "session bug"], "Bug.Auth")),
                    Subcategory("Billing", "Billing system bugs", v(["billing bug", "payment bug", "invoice bug"], "Bug.Billing")),
                    Subcategory("Collaboration", "Collaboration features", v(["collaboration bug", "sharing bug", "permissions bug"], "Bug.Collab")),
                    Subcategory("Dashboard", "Dashboard bugs", v(["dashboard bug", "ui bug", "interface bug"], "Bug.Dashboard")),
                    Subcategory("Data", "Data-related bugs", v(["data bug", "sync bug", "data loss"], "Bug.Data")),
                    Subcategory("Email", "Email functionality bugs", v(["email bug", "notification bug", "email delivery"], "Bug.Email")),
                    Subcategory("File Upload", "File upload bugs", v(["upload bug", "file bug", "attachment bug"], "Bug.Upload")),
                    Subcategory("Font", "Font-related bugs", v(["font bug", "text bug", "formatting bug"], "Bug.Font")),
                    Subcategory("Import", "Import functionality bugs", v(["import bug", "upload bug", "file import"], "Bug.Import")),
                    Subcategory("Integration", "Third-party integration bugs", v(["integration bug", "connector bug", "api bug"], "Bug.Integration")),
                    Subcategory("Mobile", "Mobile app bugs", v(["mobile bug", "app bug", "ios bug", "android bug"], "Bug.Mobile")),
                    Subcategory("Performance", "Performance issues", v(["slow", "performance", "loading", "timeout"], "Bug.Perf")),
                    Subcategory("Publishing", "Publishing bugs", v(["publish bug", "deploy bug", "publication bug"], "Bug.Publish")),
                    Subcategory("Search", "Search functionality bugs", v(["search bug", "find bug", "search not working"], "Bug.Search")),
                    Subcategory("Security", "Security-related bugs", v(["security bug", "vulnerability", "security issue"], "Bug.Security")),
                    Subcategory("Sync", "Synchronization bugs", v(["sync bug", "sync issue", "data sync"], "Bug.Sync")),
                    Subcategory("Template", "Template bugs", v(["template bug", "theme bug", "design bug"], "Bug.Template")),
                    Subcategory("UI/UX", "User interface bugs", v(["ui bug", "ux bug", "interface bug", "design bug"], "Bug.UIUX")),
                    Subcategory("Video", "Video-related bugs", v(["video bug", "media bug", "playback bug"], "Bug.Video")),
                    Subcategory("Workspace", "Workspace bugs", v(["workspace bug", "team bug", "organization bug"], "Bug.Workspace")),
                    Subcategory("Other Bug", "Other bug reports", v(["bug", "error", "issue", "problem"], "Bug.Other"))
                ]
            ),
            
            "Agent/Buddy": Category(
                name="Agent/Buddy",
                description="AI agent questions and usage (internal name: Buddy)",
                keywords=v(["agent", "buddy", "fin", "ai", "bot", "assistant"], "AgentBuddy"),
                subcategories=[
                    Subcategory("Agent Question", "Questions about AI agent", v(["agent", "fin", "ai", "bot", "assistant"], "Agent.Question")),
                    Subcategory("Agent Feedback", "Feedback on AI agent", v(["agent feedback", "fin feedback", "ai feedback"], "Agent.Feedback")),
                    Subcategory("Agent Training", "AI agent training requests", v(["agent training", "fin training", "ai training"], "Agent.Training")),
                    Subcategory("Agent Integration", "AI agent integration", v(["agent integration", "fin integration", "ai integration"], "Agent.Integration")),
                    Subcategory("Agent Performance", "AI agent performance", v(["agent performance", "fin performance", "ai performance"], "Agent.Perf")),
                    Subcategory("Other Agent", "Other AI agent issues", v(["agent", "ai", "fin", "buddy"], "Agent.Other"))
                ]
            ),
            
            "Chargeback": Category(
                name="Chargeback",
                description="Disputed or unauthorized charges",
                keywords=v(["chargeback", "dispute", "unauthorized", "fraudulent"], "Chargeback"),
                subcategories=[
                    Subcategory("Chargeback", "Chargeback disputes", v(["chargeback", "dispute", "unauthorized charge"], "Chargeback.Dispute"))
                ]
            ),
            
            "Feedback": Category(
                name="Feedback",
                description="Feature requests and suggestions",
                keywords=v(["feedback", "suggestion", "feature request", "improvement"], "Feedback"),
                subcategories=[
                    Subcategory("Feature Request", "Feature requests", v(["feature request", "new feature", "suggestion"], "Feedback.Request")),
                    Subcategory("Improvement", "Product improvements", v(["improvement", "enhancement", "better"], "Feedback.Improvement")),
                    Subcategory("User Experience", "UX feedback", v(["ux", "user experience", "usability"], "Feedback.UX")),
                    Subcategory("Other Feedback", "Other feedback", v(["feedback", "suggestion", "comment"], "Feedback.Other"))
                ]
            ),
            
            "Partnerships": Category(
                name="Partnerships",
                description="Business collaborations, affiliate programs",
                keywords=v(["partnership", "affiliate", "collaboration", "business"], "Partnerships"),
                subcategories=[
                    Subcategory("Partnership", "Partnership inquiries", v(["partnership", "collaboration", "business"], "Partnerships.Inquiry")),
                    Subcategory("Affiliate", "Affiliate program", v(["affiliate", "referral", "commission"], "Partnerships.Affiliate")),
                    Subcategory("Integration", "Integration partnerships", v(["integration", "api partnership", "connector"], "Partnerships.Integration"))
                ]
            ),
            
            "Privacy": Category(
                name="Privacy",
                description="Data protection, security, ToS, privacy policies",
                keywords=v(["privacy", "security", "data protection", "gdpr", "tos"], "Privacy"),
                subcategories=[
                    Subcategory("Privacy Policy", "Privacy policy questions", v(["privacy policy", "privacy", "data protection"], "Privacy.Policy")),
                    Subcategory("GDPR", "GDPR compliance", v(["gdpr", "data protection", "privacy rights"], "Privacy.GDPR")),
                    Subcategory("Security", "Security concerns", v(["security", "data security", "protection"], "Privacy.Security")),
                    Subcategory("Terms of Service", "Terms of service", v(["terms", "tos", "terms of service"], "Privacy.ToS"))
                ]
            ),
            
            "Product Question": Category(
                name="Product Question",
                description="How-to questions about features",
                keywords=v([
                    # English - Core terms
                    "how to", "question", "help", "tutorial", "guide",
                    
                    # English - Export/Download (311 product conversations analyzed)
                    "export", "download", "ppt", "powerpoint", "pdf", "slides", "slide",
                    "save as", "convert to", "export pdf", "export ppt", "download presentation",
                    
                    # English - Publishing/Sharing (144 publish conversations)
                    "publish", "share", "share link", "gamma link", "website", 
                    "publish site", "gamma site", "publishing", "site access",
                    "viewer", "public link", "embed", "share with",
                    
                    # English - Design/Customization (logo: 34, font: 32, theme: 22)
                    "logo", "font", "theme", "template", "color", "colours",
                    "design", "style", "customize", "layout", "background",
                    "corporate colors", "brand colors", "upload logo",
                    
                    # English - Translation/Language (32 translate conversations)
                    "translate", "translation", "language", "change language",
                    "translate presentation", "language support",
                    
                    # English - Notes/Comments (66 notes conversations)
                    "notes", "presenter notes", "speaker notes", "comments",
                    "hide notes", "viewer can't see notes",
                    
                    # English - Presentation Creation (42 new presentation conversations)
                    "new presentation", "create presentation", "accessing presentation",
                    "presentation access",
                    
                    # English - Common question patterns
                    "can you", "could you", "is there a way", "how can i",
                    
                    # Spanish (10.2% of conversations - 35 from Oct+Nov combined dataset)
                    "exportar", "descargar", "diapositivas", "presentación",
                    "publicar", "compartir", "traducir", "diseño", "tema",
                    "plantilla", "notas", "crear presentación",
                    "carga",            # upload (NEW from 2000 convs)
                    "publicación",      # publication (NEW from 2000 convs)
                    "página",           # page (NEW from 2000 convs)
                    "sitio",            # site (NEW from 2000 convs)
                    "subir",            # upload (NEW from 2000 convs)
                    "ayuda",            # help (NEW from 2000 convs)
                    
                    # Portuguese (9.5% of conversations - 51 from Oct+Nov combined dataset)
                    "exportar", "baixar", "slides", "apresentação",
                    "publicar", "compartilhar", "traduzir", "design", "tema",
                    "modelo", "notas", "criar apresentação",
                    "consigo",          # I can/I'm able (NEW from 2000 convs)
                    "gerar",            # generate (NEW from 2000 convs)
                    "fazer",            # make/do (NEW from 2000 convs)
                    "como",             # how (NEW from 2000 convs)
                    "site",             # site (NEW from 2000 convs)
                    
                    # French (6.5% of conversations - 34 from Oct+Nov combined dataset)
                    "exporter", "télécharger", "diapositives", "présentation",
                    "publier", "partager", "traduire", "thème", "modèle",
                    "page",             # page (NEW from 2000 convs)
                    "site",             # site (NEW from 2000 convs)
                    "publication",      # publication (NEW from 2000 convs)
                    "accès",            # access (NEW from 2000 convs)
                    "erreur",           # error (NEW from 2000 convs)
                    
                    # German (3.0% of conversations - 22 from Oct+Nov combined dataset)
                    "exportieren", "herunterladen", "folien", "präsentation",
                    "veröffentlichen", "teilen", "übersetzen",
                    "seite",            # page/site (NEW from 2000 convs)
                    "website",          # website (NEW from 2000 convs)
                    "bild",             # image (NEW from 2000 convs)
                    "kann",             # can (NEW from 2000 convs)
                    "beim",             # at/during (NEW from 2000 convs)
                    "diese", "dieser",  # this (NEW from 2000 convs)
                    
                    # Italian (3.5% of conversations)
                    "esportare", "scaricare", "diapositive", "presentazione",
                    "pubblicare", "condividere", "tradurre", "tema", "modello",
                    "nota", "note", "bloccato nella",

                    # Russian (5.0% of conversations)
                    "как", "вопрос", "помощь", "экспорт", "скачать",
                    "презентация", "слайд", "поделиться",

                    # Korean (9.0% of conversations)
                    "방법", "질문", "도움", "내보내기", "다운로드",
                    "프레젠테이션", "슬라이드", "공유", "어떻게"
                ], "ProductQuestion"),
                subcategories=[
                    Subcategory("How to Use", "How-to questions", v(["how to", "how do i", "tutorial", "guide"], "Product.HowTo")),
                    Subcategory("Feature Explanation", "Feature explanations", v(["what is", "explain", "feature"], "Product.Feature")),
                    Subcategory("Best Practices", "Best practices", v(["best practice", "tips", "recommendations"], "Product.BestPractices")),
                    Subcategory("Workflow", "Workflow questions", v(["workflow", "process", "steps"], "Product.Workflow")),
                    Subcategory("Integration", "Integration questions", v(["integration", "connect", "setup"], "Product.Integration")),
                    Subcategory("Customization", "Customization questions", v(["customize", "personalize", "settings"], "Product.Customization")),
                    Subcategory("Troubleshooting", "General troubleshooting", v(["troubleshoot", "help", "problem"], "Product.Troubleshooting")),
                    Subcategory("Training", "Training requests", v(["training", "learn", "education"], "Product.Training")),
                    Subcategory("Documentation", "Documentation requests", v(["documentation", "docs", "manual"], "Product.Docs")),
                    Subcategory("Support", "General support", v(["support", "help", "assistance"], "Product.Support")),
                    Subcategory("Other Product", "Other product questions", v(["question", "help", "support"], "Product.Other"))
                ]
            ),
            
            "Promotions": Category(
                name="Promotions",
                description="Discounts, special offers, coupon codes",
                keywords=v(["promotion", "discount", "coupon", "offer", "deal"], "Promotions"),
                subcategories=[
                    Subcategory("Promotion", "Promotional offers", v(["promotion", "offer", "deal", "discount"], "Promotions.Offer"))
                ]
            ),
            
            # NOTE: "Unknown" removed from detectable categories
            # It should ONLY be used as fallback when no other topics match
            # Otherwise conversations mentioning "unclear" get tagged as Unknown
            # even when they're clearly about Billing, Product, etc.
            
            "Workspace": Category(
                name="Workspace",
                description="Member management, permissions, sharing",
                keywords=v([
                    # English - Core terms
                    "workspace", "team", "member", "permission", "sharing",
                    
                    # English - Domain/Site management (80 workspace conversations analyzed)
                    "domain", "custom domain", "gamma domain", "website", "site",
                    "site settings", "website settings", "company name", "organization",
                    
                    # English - Team collaboration
                    "team workspace", "company workspace", "workspace settings",
                    "team settings", "collaborate", "collaboration",
                    
                    # English - Common phrases (from real data)
                    "company details", "the company", "company name",
                    
                    # Spanish (10.2% of conversations)
                    "espacio de trabajo", "equipo", "dominio", "sitio web",
                    "configuración del equipo", "organización",
                    
                    # Portuguese (9.5% of conversations)
                    "espaço de trabalho", "equipe", "domínio", "site",
                    "configurações da equipe", "organização",
                    
                    # French (6.5% of conversations)
                    "espace de travail", "équipe", "domaine", "site web",
                    "paramètres de l'équipe", "organisation",
                    
                    # German (3.0% of conversations)
                    "Arbeitsbereich", "Team", "Domäne", "Website",
                    "Teameinstellungen", "Organisation",
                    
                    # Italian (3.5% of conversations)
                    "spazio di lavoro", "squadra", "dominio", "sito web",
                    "impostazioni del team", "organizzazione",

                    # Russian (5.0% of conversations)
                    "рабочее пространство", "команда", "участник",
                    "пригласить", "настройки",

                    # Korean (9.0% of conversations)
                    "워크스페이스", "팀", "멤버", "초대",
                    "설정", "조직"
                ], "Workspace"),
                subcategories=[
                    Subcategory("Member Management", "Member management", v(["member", "team", "user management"], "Workspace.Member")),
                    Subcategory("Permissions", "Permission management", v(["permission", "access", "role", "admin"], "Workspace.Permissions"))
                ]
            )
        }
    
    def _load_from_yaml(self):
        """Load taxonomy from YAML file."""
        with open(self.taxonomy_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Convert YAML data back to Category objects
        for cat_name, cat_data in data['categories'].items():
            subcategories = []
            for sub_data in cat_data['subcategories']:
                subcategories.append(Subcategory(**sub_data))
            
            self.categories[cat_name] = Category(
                name=cat_name,
                description=cat_data['description'],
                keywords=cat_data['keywords'],
                confidence_threshold=cat_data.get('confidence_threshold', 0.7),
                subcategories=subcategories
            )
    
    def _save_to_yaml(self):
        """Save taxonomy to YAML file."""
        data = {
            'categories': {}
        }
        
        for cat_name, category in self.categories.items():
            data['categories'][cat_name] = {
                'description': category.description,
                'keywords': category.keywords,
                'confidence_threshold': category.confidence_threshold,
                'subcategories': [
                    {
                        'name': sub.name,
                        'description': sub.description,
                        'keywords': sub.keywords,
                        'confidence_threshold': sub.confidence_threshold
                    }
                    for sub in category.subcategories
                ]
            }
        
        with open(self.taxonomy_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, indent=2)
    
    def get_category(self, name: str) -> Optional[Category]:
        """Get a category by name."""
        return self.categories.get(name)
    
    def get_all_categories(self) -> List[str]:
        """Get all category names."""
        return list(self.categories.keys())
    
    def classify_conversation(self, conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Classify a conversation into categories based on tags, topics, and text.
        
        Args:
            conversation: Conversation data from Intercom
        
        Returns:
            List of classification results with confidence scores
        """
        classifications = []
        
        # Extract text for analysis
        full_text = self._extract_conversation_text(conversation)
        text_lower = full_text.lower()
        
        # Get tags and topics
        tags = self._extract_tags(conversation)
        topics = self._extract_topics(conversation)
        
        # Classify based on tags and topics first (high confidence)
        for tag in tags:
            classification = self._classify_by_keyword(tag, "tagged")
            if classification:
                classifications.append(classification)
        
        for topic in topics:
            classification = self._classify_by_keyword(topic, "tagged")
            if classification:
                classifications.append(classification)
        
        # Classify based on text content (lower confidence)
        for category_name, category in self.categories.items():
            confidence = self._calculate_text_confidence(text_lower, category)
            if confidence >= category.confidence_threshold:
                classifications.append({
                    'category': category_name,
                    'subcategory': 'General',
                    'confidence': confidence,
                    'method': 'text_analysis',
                    'keywords_found': self._find_matching_keywords(text_lower, category.keywords)
                })
        
        # Remove duplicates and sort by confidence
        unique_classifications = {}
        for classification in classifications:
            key = f"{classification['category']}_{classification['subcategory']}"
            if key not in unique_classifications or classification['confidence'] > unique_classifications[key]['confidence']:
                unique_classifications[key] = classification
        
        return sorted(unique_classifications.values(), key=lambda x: x['confidence'], reverse=True)
    
    def _extract_conversation_text(self, conversation: Dict[str, Any]) -> str:
        """Extract full text from conversation."""
        from src.utils.conversation_utils import extract_conversation_text
        return extract_conversation_text(conversation, clean_html=True)
    
    def _extract_tags(self, conversation: Dict[str, Any]) -> List[str]:
        """Extract tags from conversation."""
        tags = []
        tags_data = conversation.get('tags', {}).get('tags', [])
        
        for tag in tags_data:
            if isinstance(tag, dict):
                tags.append(tag.get('name', str(tag)))
            else:
                tags.append(str(tag))
        
        return tags
    
    def _extract_topics(self, conversation: Dict[str, Any]) -> List[str]:
        """Extract topics from conversation."""
        topics = []
        topics_data = conversation.get('topics', {}).get('topics', [])
        
        for topic in topics_data:
            if isinstance(topic, dict):
                topics.append(topic.get('name', str(topic)))
            else:
                topics.append(str(topic))
        
        return topics
    
    def _classify_by_keyword(self, keyword: str, method: str) -> Optional[Dict[str, Any]]:
        """Classify based on a single keyword."""
        keyword_lower = keyword.lower()
        
        for category_name, category in self.categories.items():
            # Check category keywords
            if any(cat_keyword.lower() in keyword_lower for cat_keyword in category.keywords):
                return {
                    'category': category_name,
                    'subcategory': 'General',
                    'confidence': 1.0,
                    'method': method,
                    'keywords_found': [keyword]
                }
            
            # Check subcategory keywords
            for subcategory in category.subcategories:
                if any(sub_keyword.lower() in keyword_lower for sub_keyword in subcategory.keywords):
                    return {
                        'category': category_name,
                        'subcategory': subcategory.name,
                        'confidence': 1.0,
                        'method': method,
                        'keywords_found': [keyword]
                    }
        
        return None
    
    def _calculate_text_confidence(self, text: str, category: Category) -> float:
        """Calculate confidence score based on text content."""
        matching_keywords = self._find_matching_keywords(text, category.keywords)
        
        if not matching_keywords:
            return 0.0
        
        # Simple confidence calculation based on keyword matches
        confidence = min(len(matching_keywords) / len(category.keywords), 1.0)
        
        # Boost confidence for exact matches
        exact_matches = sum(1 for keyword in matching_keywords if keyword in text)
        confidence += exact_matches * 0.1
        
        return min(confidence, 1.0)
    
    def _find_matching_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """Find keywords that match in the text."""
        matching = []
        for keyword in keywords:
            if keyword.lower() in text:
                matching.append(keyword)
        return matching
    
    def update_taxonomy(self, new_items: Dict[str, Any]):
        """Update taxonomy with new items discovered from data."""
        # This will be implemented to handle dynamic taxonomy updates
        pass

    def test_multilingual_keywords(self):
        """
        Test method to verify that multi-language keywords (Russian, Korean) are working.
        Logs debug info about keyword integrity.
        """
        test_keywords = {
            "Russian": ["аккаунт", "пароль"],
            "Korean": ["계정", "비밀번호"]
        }
        
        for lang, keys in test_keywords.items():
            for key in keys:
                # Check if keyword exists in any category
                found = False
                for cat in self.categories.values():
                    if key in cat.keywords:
                        found = True
                        break
                
                if found:
                    logger.debug(f"✅ {lang} keyword '{key}' verified in taxonomy")
                else:
                    logger.warning(f"⚠️ {lang} keyword '{key}' MISSING from taxonomy")

# Global taxonomy manager instance
taxonomy_manager = TaxonomyManager()
