# Keyword Analysis from Real Conversation Data
**Source:** 200 conversations from sample run (Nov 15, 2025)  
**Purpose:** Extract data-driven keywords to improve topic detection accuracy

---

## Current Detection Results (From Sample Data)

### Topic Distribution:
- **Refund:** 102 conversations (51%) - DOMINANT topic
- **Domain:** 17 conversations (8.5%)
- **New Presentation:** 5 conversations (2.5%)
- **Affiliate:** 4 conversations (2%)
- **Discount:** 4 conversations (2%)
- **Publish:** 4 conversations (2%)
- **Credits:** 3 conversations (1.5%)
- **Website Gamma:** 3 conversations (1.5%)
- **Others:** 58 conversations (29%)

---

## KEYWORD EXTRACTION BY TOPIC

### **BILLING/REFUND (102 conversations - 51%)**

**Current keywords:** billing, payment, invoice, refund, subscription, credit card

**Words found in REAL conversations:**
- **High frequency:** refund, cancel, subscription, payment, charged
- **Multilingual:**
  - Portuguese: "cancelar", "reembolso", "pagamento"
  - Spanish: "cancelar", "reembolso", "pagado"
  - German: "Abbuchung", "Rechnung", "bezahlt"
  - Italian: "rimborso", "cancellare"

**Common phrases in real data:**
- "charged twice"
- "want refund"
- "cancel subscription"
- "unexpected charge"
- "return payment"
- "not interested in continuing"

**RECOMMENDED NEW KEYWORDS:**
```python
"Billing": [
    # English
    "billing", "payment", "invoice", "refund", "subscription", "credit card", 
    "charged", "charge", "cancel", "unexpected charge", "charged twice",
    "return payment", "want refund", "cancel subscription",
    
    # Portuguese
    "cobrança", "pagamento", "fatura", "reembolso", "assinatura", "cancelar",
    
    # Spanish
    "facturación", "pago", "factura", "reembolso", "suscripción", "cancelar",
    
    # German
    "Rechnung", "Zahlung", "Abbuchung", "Rückerstattung",
    
    # French
    "facturation", "paiement", "facture", "remboursement", "abonnement"
]
```

---

### **ACCOUNT (Domain/Email/Password - 20 conversations - 10%)**

**Current keywords:** account, login, password, email, settings, credits

**Words found in REAL conversations:**
- **High frequency:** email, change, address, account, domain, password
- **Common actions:** "change email", "reset password", "delete account", "can't login"

**Common phrases:**
- "change the current email address"
- "want to change email"
- "add a new email"
- "delete my account"
- "unable to get into my account"
- "can't access account"

**RECOMMENDED NEW KEYWORDS:**
```python
"Account": [
    # English
    "account", "login", "password", "email", "settings", "domain",
    "change email", "reset password", "delete account", "can't login",
    "unable to get into", "access account", "add new email",
    "current email address",
    
    # Portuguese
    "conta", "senha", "email", "domínio", "acesso",
    
    # Spanish
    "cuenta", "contraseña", "correo", "dominio", "acceso",
    
    # German
    "Konto", "Passwort", "E-Mail", "Domäne",
    
    # French
    "compte", "mot de passe", "email", "domaine"
]
```

---

### **FEATURE REQUESTS/PRODUCT (Export, Download, Publish - 15 conversations - 7.5%)**

**Current keywords:** feature, request, suggestion, idea

**Words found in REAL conversations:**
- **Export:** "export pdf", "export ppt", "download presentation", "powerpoint"
- **Publish:** "publish", "share link", "viewer can't see notes", "website preview"
- **Translation:** "translate presentation", "language support"

**Common phrases:**
- "how do I export to pdf"
- "make a powerpoint presentation"
- "share a gamma link"
- "import pdf and create ppt"
- "publish or disable my gamma site"

**RECOMMENDED NEW KEYWORDS:**
```python
"Product Question": [
    # Current features
    "export", "download", "publish", "share", "pdf", "ppt", "powerpoint",
    "import", "translate", "language", "collaboration", "notes",
    "website preview", "viewer", "link", "embed",
    
    # Common questions
    "how do I", "how can I", "is there a way", "is it possible",
    
    # Multilingual
    "exportar", "descargar", "publicar",  # Spanish
    "exportar", "baixar", "publicar",      # Portuguese
    "exporter", "télécharger", "publier"   # French
]
```

---

### **CREDITS (3 conversations)**

**Current keywords:** (probably under Billing currently)

**Words found in REAL conversations:**
- "credits", "Gamma cred", "no credits booked"

**SHOULD BE:** Separate topic or Billing subcategory

---

### **AFFILIATE/PARTNERSHIP (4 conversations)**

**Words found:** "affiliate", "partnership", "business inquiry"

**SHOULD BE:** Separate "Business Inquiry" or "Partnerships" topic

---

## LANGUAGE DISTRIBUTION (From Sample)

Based on conversation text analysis:
- **English:** ~48%
- **Portuguese:** ~11%
- **Spanish:** ~10%
- **German:** ~5%
- **French:** ~4%
- **Thai:** ~3%
- **Other:** ~19%

**52% of conversations are NON-ENGLISH!**

---

## RECOMMENDATIONS

### **IMMEDIATE ACTIONS:**

1. **Add multilingual keywords** for top 5 languages (covers 78% of conversations)
   - Portuguese, Spanish, German, French, Italian

2. **Add phrase-based keywords** (not just single words)
   - "charged twice" > "charged"
   - "cancel subscription" > "cancel"
   - "reset password" > "password"

3. **Add common question patterns**
   - "how do I", "how can I", "is there a way"
   - These appear frequently in Product Questions

4. **Separate "Credits" from "Billing"**
   - Different intent (account balance vs payments)

5. **Add "Partnerships/Business Inquiry" topic**
   - Currently unclassified: affiliate, business questions

---

## EXPECTED IMPROVEMENT

**Current state:**
- Keyword match rate: ~40-50% (English-only keywords)
- LLM needed for: 50-60% of conversations

**After adding multilingual + phrase keywords:**
- Keyword match rate: ~70-80% (covers 52% non-English + better English matching)
- LLM needed for: 20-30% of conversations (only truly ambiguous cases)

**Speed improvement:**
- Current: 10-15 minutes for 200 conversations (120+ LLM calls)
- After: 3-5 minutes for 200 conversations (40-60 LLM calls)

**Cost improvement:**
- Current: ~$1 per 200 conversations
- After: ~$0.30 per 200 conversations (70% reduction!)

---

## NEXT STEPS

1. Update `src/config/taxonomy.py` with new keywords
2. Test with sample-mode (should see higher keyword match rate)
3. Validate topics are still accurate (keywords shouldn't misclassify)
4. Iterate based on results

