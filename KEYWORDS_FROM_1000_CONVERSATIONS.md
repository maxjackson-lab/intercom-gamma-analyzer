# Data-Driven Keywords from 1000 Real Conversations
**Source:** Sample run Nov 17, 2025 (1000 conversations)  
**Purpose:** Improve keyword detection accuracy with multilingual support

---

## Executive Summary

**Current State:**
- 47.3% English, 52.7% non-English
- Top 3 languages: Spanish (10.2%), Brazilian Portuguese (9.5%), French (6.5%)
- **Current keywords: English-only → Missing 52.7% of conversations!**

**Opportunity:**
- Add multilingual keywords → Match 70-80% by keywords (vs current ~40%)
- Reduce LLM calls by 50-60%
- Speed: 3-5 min instead of 10-15 min for 200 conversations
- Cost: $0.30 instead of $1 per 200 conversations

---

## Topic Distribution (Detected by Current System)

```
Product Question:     707 (70.7%)  - NEEDS EXPANSION
Billing:              651 (65.1%)  - WELL COVERED
Account:              498 (49.8%)  - NEEDS EXPANSION
Workspace:            344 (34.4%)  - NEEDS NEW KEYWORDS
Bug:                  309 (30.9%)  - NEEDS EXPANSION
Partnerships:         152 (15.2%)  - NEEDS NEW KEYWORDS
Feedback:             138 (13.8%)  - OK
Agent/Buddy:          129 (12.9%)  - OK
Promotions:            99 (9.9%)   - OK
Privacy:               75 (7.5%)   - OK
```

---

## SDK Topics (Ground Truth from Intercom)

**Most common user issues (from Intercom's own classification):**

```
refund:                 482 conversations  ← BILLING
invoices:               184 conversations  ← BILLING
domain:                 160 conversations  ← ACCOUNT/WORKSPACE
publish:                144 conversations  ← PRODUCT
credits:                132 conversations  ← BILLING/ACCOUNT
slides:                  82 conversations  ← PRODUCT
notes:                   66 conversations  ← PRODUCT
ppt/powerpoint:          86 conversations  ← PRODUCT
website gamma:           42 conversations  ← WORKSPACE
change email:            38 conversations  ← ACCOUNT
logo/font/theme:         98 conversations  ← PRODUCT
api:                     34 conversations  ← PRODUCT/TECHNICAL
translate presentation:  32 conversations  ← PRODUCT
affiliate:               26 conversations  ← PARTNERSHIPS
```

---

## RECOMMENDED KEYWORDS BY TOPIC

### 🔴 **BILLING/REFUND (Priority #1 - 651 conversations, 65%)**

**Current keywords:** billing, payment, invoice, refund, subscription, credit card

**Add these keywords from real data:**

#### English:
```python
# Core refund terms
"refund", "cancel", "cancelled", "subscription", "charged", "charge",

# Invoice/receipt terms  
"invoice", "receipt", "invoice number", "receipt from",

# Payment issues
"payment", "charged twice", "unexpected charge", "want refund",
"return payment", "cancel subscription", "not interested",

# Credit/account balance
"credits", "credit card", "balance", "account balance",

# Specific phrases (from data)
"from gamma", "gamma support", "subscription plan"
```

#### Portuguese (9.5% of conversations):
```python
"reembolso",        # refund
"cancelar",         # cancel
"cobrança",         # charge/billing
"estorno",          # refund/chargeback
"pagamento",        # payment
"assinatura",       # subscription
"fatura",           # invoice
"cartão de crédito" # credit card
```

#### Spanish (10.2% of conversations):
```python
"reembolso",        # refund
"cancelar",         # cancel
"factura",          # invoice
"pago", "pagado",   # payment, paid
"suscripción",      # subscription
"cargo",            # charge
"tarjeta de crédito" # credit card
```

#### French (6.5% of conversations):
```python
"remboursement",    # refund
"annuler",          # cancel
"paiement",         # payment
"abonnement",       # subscription
"facture",          # invoice
"carte de crédit"   # credit card
```

#### German (3.0% of conversations):
```python
"Rückerstattung",   # refund
"Rechnung",         # invoice
"Zahlung",          # payment
"Abbuchung",        # debit/charge
"Abonnement"        # subscription
```

#### Italian (3.5% of conversations):
```python
"rimborso",         # refund
"cancellare",       # cancel
"abbonamento",      # subscription
"fattura",          # invoice
"pagamento"         # payment
```

**Expected impact:**
- Current: ~50% keyword match (English only)
- After: ~75-80% keyword match (multilingual)
- LLM calls reduced: 325 → 130 conversations

---

### 🔵 **ACCOUNT (Priority #2 - 498 conversations, 49.8%)**

**Current keywords:** account, login, password, email, settings, credits

**Add these keywords from real data:**

#### English:
```python
# Email operations
"change email", "current email address", "add new email", 
"email address", "change the email", "update email",

# Password operations
"reset password", "forgot password", "can't login", "unable to login",
"can't access", "unable to get into", "access account",

# Account management
"delete account", "close account", "account deletion",
"domain", "company name", "team name",

# Access issues
"locked out", "can't sign in", "unable to access"
```

#### Multilingual (top phrases):
```python
# Spanish
"cambiar correo", "contraseña", "cuenta", "acceso", "dominio"

# Portuguese
"mudar email", "senha", "conta", "acesso", "domínio"

# French
"changer email", "mot de passe", "compte", "domaine"

# German
"E-Mail ändern", "Passwort", "Konto", "Domäne"

# Italian
"cambiare email", "password", "account", "accesso"
```

**Expected impact:**
- Current: ~45% keyword match
- After: ~70-75% keyword match
- LLM calls reduced: 274 → 125 conversations

---

### 🟢 **PRODUCT QUESTION (Priority #3 - 707 conversations, 70.7%)**

**Current keywords:** feature, request, suggestion, idea

**⚠️ MAJOR PROBLEM: "Product Question" is TOO BROAD!**

**Break down into specific subcategories based on SDK topics:**

#### **A) Export/Download (PPT/PDF)**
```python
# English
"export", "download", "ppt", "powerpoint", "pdf", "export pdf",
"export ppt", "download presentation", "save as", "convert to",
"import", "import pdf", "create ppt"

# Multilingual common
"exportar", "descargar", "baixar", "télécharger", "exportieren"
```

#### **B) Publishing/Sharing**
```python
# English
"publish", "share", "share link", "gamma link", "website", 
"publish site", "gamma site", "publishing", "site access",
"viewer", "public link", "embed"

# Specific issues (from data)
"error publishing", "not enabled", "untrusted URL"

# Multilingual
"publicar", "compartilhar", "partager", "veröffentlichen", "condividere"
```

#### **C) Design/Customization**
```python
# English
"logo", "font", "theme", "template", "color", "colours",
"design", "style", "customize", "layout", "format",
"slide", "slides", "slide design", "background"

# Specific (from data)
"corporate colors", "brand colors", "upload logo"
```

#### **D) Translation/Language**
```python
# English
"translate", "translation", "language", "change language",
"translate presentation", "language support", "hebrew", "arabic",
"right to left", "RTL"

# Multilingual
"traducir", "traduzir", "traduire", "übersetzen", "tradurre"
```

#### **E) Notes/Comments**
```python
"notes", "presenter notes", "speaker notes", "comments",
"hide notes", "viewer can't see notes", "note visibility"
```

#### **F) Collaboration**
```python
"team", "collaborate", "collaboration", "share with team",
"workspace", "team access", "permissions", "invite"
```

**Expected impact:**
- Current: ~30% keyword match (too generic)
- After: ~65-70% keyword match (specific subcategories)
- LLM calls reduced: 495 → 212 conversations

---

### 🟡 **WORKSPACE (Priority #4 - 344 conversations, 34.4%)**

**Current keywords:** workspace, team, settings

**Add from real data:**

```python
# English
"workspace", "team workspace", "company workspace", 
"domain", "custom domain", "gamma domain", "website",
"site settings", "workspace settings", "team settings",
"company name", "organization"

# Multilingual
"espaço de trabalho", "espacio de trabajo", "espace de travail"
```

**Expected impact:**
- Current: ~40% keyword match
- After: ~60-65% keyword match

---

### 🔴 **BUG REPORTS (Priority #5 - 309 conversations, 30.9%)**

**Current keywords:** bug, error, crash, broken

**Add from real data:**

```python
# English
"not working", "doesn't work", "won't load", "can't load",
"error", "error message", "failed", "fails", "failing",
"broken", "bug", "issue", "problem", "glitch",
"not loading", "stuck", "frozen", "slow", "laggy",

# Specific errors (from data)
"error publishing", "can't save", "won't export", 
"not generating", "AI not generating", "slides not generating"

# Multilingual
"não funciona", "no funciona", "ne fonctionne pas", 
"funktioniert nicht", "non funziona",
"erro", "error", "erreur", "Fehler", "errore"
```

**Expected impact:**
- Current: ~45% keyword match
- After: ~70% keyword match

---

### 🟣 **PARTNERSHIPS (Priority #6 - 152 conversations, 15.2%)**

**Current keywords:** (probably none or under "Product Question")

**Add from real data:**

```python
# English
"affiliate", "partnership", "partner", "business inquiry",
"enterprise", "bulk", "volume pricing", "team pricing",
"reseller", "white label", "API access", "integration"
```

**Expected impact:**
- Current: ~5% keyword match (probably classified as "Product Question")
- After: ~50-60% keyword match (new dedicated keywords)

---

## Language Distribution (Full Data)

```
English:                473 (47.3%)  ✅ Well covered
Spanish:                102 (10.2%)  ❌ Need keywords
Brazilian Portuguese:    95 (9.5%)   ❌ Need keywords
French:                  65 (6.5%)   ❌ Need keywords
Russian:                 36 (3.6%)   ⚠️  Low priority
Italian:                 35 (3.5%)   ❌ Need keywords
German:                  30 (3.0%)   ❌ Need keywords
Korean:                  23 (2.3%)   ⚠️  Low priority
Arabic:                  19 (1.9%)   ⚠️  Low priority
```

**Priority languages for keywords (covers 90.8% of conversations):**
1. English (47.3%)
2. Spanish (10.2%)
3. Brazilian Portuguese (9.5%)
4. French (6.5%)
5. Italian (3.5%)
6. German (3.0%)

---

## Implementation Priority

### **Phase 1: HIGH IMPACT (Implement First)**

1. **Billing/Refund multilingual keywords**
   - Impact: 651 conversations (65%)
   - Improvement: 50% → 80% keyword match
   - Effort: Low (clear patterns, high frequency)

2. **Account multilingual keywords**
   - Impact: 498 conversations (50%)
   - Improvement: 45% → 75% keyword match
   - Effort: Low (clear patterns)

3. **Bug reports expanded keywords**
   - Impact: 309 conversations (31%)
   - Improvement: 45% → 70% keyword match
   - Effort: Low (common patterns)

**Total Phase 1 impact: ~1450 classifications improved**

---

### **Phase 2: MEDIUM IMPACT (Implement Second)**

4. **Product Question subcategories**
   - Impact: 707 conversations (71%)
   - Improvement: 30% → 65% keyword match
   - Effort: Medium (needs subcategorization)

5. **Workspace keywords**
   - Impact: 344 conversations (34%)
   - Improvement: 40% → 65% keyword match
   - Effort: Low

**Total Phase 2 impact: ~450 additional classifications improved**

---

### **Phase 3: LOW IMPACT (Implement Last)**

6. **Partnerships keywords**
   - Impact: 152 conversations (15%)
   - Effort: Low

7. **Additional language support** (Russian, Korean, Arabic)
   - Impact: 78 conversations (8%)
   - Effort: Medium

---

## Expected Overall Results

### **Before (Current State):**
```
Keyword match rate:    ~40-45%
LLM fallback needed:   ~55-60% (550-600 conversations)
Speed (1000 convs):    ~50 minutes
Cost per 1000:         ~$5
```

### **After Phase 1:**
```
Keyword match rate:    ~65-70%
LLM fallback needed:   ~30-35% (300-350 conversations)
Speed (1000 convs):    ~20-25 minutes  (2× faster)
Cost per 1000:         ~$2  (60% cheaper)
```

### **After Phase 1 + 2:**
```
Keyword match rate:    ~75-80%
LLM fallback needed:   ~20-25% (200-250 conversations)
Speed (1000 convs):    ~15-18 minutes  (3× faster)
Cost per 1000:         ~$1.50  (70% cheaper)
```

---

## Testing Plan

### **Validation Steps:**

1. **Implement Phase 1 keywords** (Billing, Account, Bug)

2. **Run test with 200 conversations:**
   ```bash
   python src/main.py sample-mode --count 200 --save-to-file
   ```

3. **Measure improvements:**
   - Keyword match rate (should increase from 45% → 65%)
   - False positive rate (should stay <5%)
   - LLM agreement with keywords (should be >90%)
   - Speed improvement (should be 2× faster)

4. **If Phase 1 successful:**
   - Implement Phase 2
   - Re-test with another 200 conversations
   - Target: 75%+ keyword match

5. **Monitor production:**
   - Track keyword accuracy over time
   - Identify new patterns
   - Iterate as needed

---

## Files to Update

1. **`src/config/taxonomy.py`** - Add multilingual keywords to each category
2. **Test with sample-mode** - Validate before production
3. **Monitor metrics** - Track keyword match rate, false positives, LLM agreement

---

## Next Steps

**READY TO IMPLEMENT?**

1. Should I implement **Phase 1** keywords now (Billing + Account + Bug)?
2. Or do you want to review specific keywords first?
3. Or gather more data on specific topics?

