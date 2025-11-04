# Intercom SDK Schema Analysis
## What We're Pulling vs. What's Available

Generated: 2025-11-03

---

## 📊 SCHEMA COMPARISON TABLE

| Field | Available in SDK | Currently Fetched | Used in Analysis | Critical For | Notes |
|-------|-----------------|-------------------|------------------|--------------|-------|
| **TOP-LEVEL CONVERSATION FIELDS** |
| `id` | ✅ | ✅ | ✅ | Everything | Primary key |
| `type` | ✅ | ✅ | ❌ | - | Always "conversation" |
| `title` | ✅ | ✅ | ❌ | - | Rarely populated |
| `created_at` | ✅ | ✅ | ✅ | Date filtering, resolution time | Unix timestamp |
| `updated_at` | ✅ | ✅ | ✅ | Resolution time, freshness | Unix timestamp |
| `waiting_since` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Customer wait time tracking |
| `snoozed_until` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Follow-up tracking |
| `open` | ✅ | ✅ | ⚠️ | State tracking | Boolean, redundant with `state` |
| `state` | ✅ | ✅ | ✅ | FCR, resolution | "open", "closed", "snoozed" |
| `read` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Admin attention tracking |
| `priority` | ✅ | ✅ | ❌ | **OPPORTUNITY** | "priority" or "not_priority" |
| `admin_assignee_id` | ✅ | ✅ | ✅ | Agent attribution, human detection | Null if unassigned |
| `team_assignee_id` | ✅ | ✅ | ⚠️ | Team routing | String ID |
| **NESTED OBJECTS** |
| `tags.tags[]` | ✅ | ✅ | ✅ | Topic detection (secondary) | Array of tag objects |
| `conversation_rating` | ✅ | ✅ | ✅ | CSAT, sentiment | Null if no rating |
| `conversation_rating.rating` | ✅ | ✅ | ✅ | CSAT score | 1-5 scale |
| `conversation_rating.remark` | ✅ | ✅ | ⚠️ | **OPPORTUNITY** | Customer feedback text |
| `conversation_rating.contact` | ✅ | ✅ | ❌ | - | Contact who rated |
| `conversation_rating.teammate` | ✅ | ✅ | ❌ | - | Admin who was rated |
| `source` | ✅ | ✅ | ✅ | First message extraction | Initial customer message |
| `source.body` | ✅ | ✅ | ✅ | Text extraction | HTML content |
| `source.author` | ✅ | ✅ | ⚠️ | Agent attribution | Author metadata |
| `source.delivered_as` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Channel tracking (email, chat, etc.) |
| `contacts.contacts[]` | ✅ | ✅ (enriched) | ✅ | Customer identification | Array of contact objects |
| `contacts.contacts[].email` | ✅ | ✅ | ⚠️ | Customer tracking | |
| `contacts.contacts[].custom_attributes` | ✅ | ✅ | ✅ | Tier, segmentation | |
| `contacts.contacts[].segments` | ✅ | ✅ (enriched) | ❌ | **OPPORTUNITY** | Customer segments |
| `teammates.teammates[]` | ✅ | ✅ | ❌ | **OPPORTUNITY** | All admins involved |
| `teammates.admins[]` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Admin metadata |
| `custom_attributes` | ✅ | ✅ | ✅ | Topic detection (primary) | Key-value pairs |
| `custom_attributes['Reason for contact']` | ✅ | ✅ | ✅ | Topic detection | Primary topic signal |
| `custom_attributes['Billing']` | ✅ | ✅ | ✅ | Subtopic detection | |
| `custom_attributes['Refund']` | ✅ | ✅ | ✅ | Subtopic detection | |
| `custom_attributes['CX Score rating']` | ✅ | ✅ | ⚠️ | Quality score | 1-5 rating |
| `custom_attributes['CX Score explanation']` | ✅ | ✅ | ⚠️ | **OPPORTUNITY** | AI-generated quality assessment |
| `custom_attributes['Fin AI Agent resolution state']` | ✅ | ✅ | ✅ | Fin performance | "Routed to team", "Assumed Resolution" |
| `custom_attributes['Language']` | ✅ | ✅ | ⚠️ | Segmentation | Multi-language support detection |
| `first_contact_reply` | ✅ | ✅ | ❌ | **OPPORTUNITY** | First response time tracking |
| `first_contact_reply.created_at` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Response time SLA |
| `first_contact_reply.url` | ✅ | ✅ | ❌ | - | Link to first reply |
| `sla_applied` | ✅ | ✅ | ❌ | **MAJOR OPPORTUNITY** | SLA breach tracking |
| `sla_applied.sla_name` | ✅ | ✅ | ❌ | **MAJOR OPPORTUNITY** | Which SLA policy |
| `sla_applied.sla_status` | ✅ | ✅ | ❌ | **MAJOR OPPORTUNITY** | "hit", "missed", "active" |
| `statistics` | ✅ | ✅ | ✅ | Performance metrics | Conversation metrics |
| `statistics.time_to_assignment` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Routing efficiency |
| `statistics.time_to_admin_reply` | ✅ | ✅ | ✅ | Response time | Seconds |
| `statistics.time_to_first_close` | ✅ | ✅ | ⚠️ | Resolution time | Seconds |
| `statistics.time_to_last_close` | ✅ | ✅ | ✅ | Resolution time | Seconds |
| `statistics.median_time_to_reply` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Average responsiveness |
| `statistics.first_contact_reply_at` | ✅ | ✅ | ⚠️ | Response time | Timestamp |
| `statistics.first_assignment_at` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Routing time |
| `statistics.first_admin_reply_at` | ✅ | ✅ | ⚠️ | Response time | Timestamp |
| `statistics.first_close_at` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Resolution time |
| `statistics.last_assignment_at` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Reassignment tracking |
| `statistics.last_contact_reply_at` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Customer engagement |
| `statistics.last_admin_reply_at` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Latest admin activity |
| `statistics.last_close_at` | ✅ | ✅ | ⚠️ | Resolution time | Timestamp |
| `statistics.last_closed_by_id` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Who closed it |
| `statistics.count_reopens` | ✅ | ✅ | ✅ | FCR calculation | Critical metric |
| `statistics.count_assignments` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Handoff tracking |
| `statistics.count_conversation_parts` | ✅ | ✅ | ✅ | Complexity | Number of messages |
| **CONVERSATION PARTS** (CRITICAL - just added!) |
| `conversation_parts.conversation_parts[]` | ✅ | ✅ **NEW!** | ✅ | Sal detection, full text | **JUST ADDED - was 0%** |
| `conversation_parts[].id` | ✅ | ✅ | ❌ | - | Part ID |
| `conversation_parts[].part_type` | ✅ | ✅ | ❌ | **OPPORTUNITY** | "comment", "note", etc. |
| `conversation_parts[].body` | ✅ | ✅ | ✅ | Text extraction | HTML content |
| `conversation_parts[].created_at` | ✅ | ✅ | ⚠️ | Message timing | Timestamp |
| `conversation_parts[].author` | ✅ | ✅ | ✅ | **Sal detection** | Author metadata |
| `conversation_parts[].author.type` | ✅ | ✅ | ✅ | **Sal detection** | "admin", "user", "bot" |
| `conversation_parts[].author.name` | ✅ | ✅ | ✅ | **Sal detection** | "Support Sal" |
| `conversation_parts[].author.email` | ✅ | ✅ | ✅ | **Sal detection** | "sal@gamma.app" |
| `conversation_parts[].attachments[]` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Attachment tracking |
| `conversation_parts[].redacted` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Privacy compliance |
| **AI AGENT (FIN) DATA** |
| `ai_agent_participated` | ✅ | ✅ | ✅ | Fin detection | Boolean |
| `ai_agent.source_type` | ✅ | ✅ | ⚠️ | Fin workflow tracking | "workflow", "answer" |
| `ai_agent.source_title` | ✅ | ✅ | ⚠️ | Fin workflow tracking | "Fin Over Messenger" |
| `ai_agent.last_answer_type` | ✅ | ✅ | ⚠️ | Fin answer quality | "ai_answer", "handoff", etc. |
| `ai_agent.resolution_state` | ✅ | ✅ | ✅ | **Fin performance** | "routed_to_team", "assumed_resolution" |
| `ai_agent.content_sources` | ✅ | ✅ | ❌ | **MAJOR OPPORTUNITY** | Which articles Fin used |
| `ai_agent.content_sources[].content_type` | ✅ | ✅ | ❌ | **MAJOR OPPORTUNITY** | "article", "content_snippet" |
| `ai_agent.content_sources[].title` | ✅ | ✅ | ❌ | **MAJOR OPPORTUNITY** | Article name |
| `ai_agent.content_sources[].url` | ✅ | ✅ | ❌ | **MAJOR OPPORTUNITY** | Article link |
| `ai_agent.created_at` | ✅ | ✅ | ❌ | **OPPORTUNITY** | When Fin engaged |
| `ai_agent.updated_at` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Last Fin activity |
| **LINKED OBJECTS** |
| `linked_objects.data[]` | ✅ | ✅ | ❌ | **OPPORTUNITY** | Tickets, articles linked | 
| **NOT AVAILABLE IN SEARCH API** |
| `topics.topics[]` | ✅ | ✅ | ⚠️ | Topic hints | Intercom's auto-topics |

---

## 🎯 CURRENT USAGE BREAKDOWN

### ✅ **HEAVILY USED** (Core Analysis)
- `id`, `created_at`, `updated_at`, `state`
- `custom_attributes` (Reason for contact, Billing, Refund, Fin resolution state)
- `conversation_parts` (Sal detection, full text) **[JUST ADDED]**
- `admin_assignee_id` (human admin detection)
- `ai_agent_participated`, `ai_agent.resolution_state`
- `conversation_rating.rating`
- `statistics.count_reopens` (FCR)
- `statistics.time_to_admin_reply`, `statistics.time_to_last_close`
- `tags` (secondary topic detection)

### ⚠️ **PARTIALLY USED** (Some fields unused)
- `contacts` (we fetch but underutilize)
- `statistics` (only using 3 out of 20+ fields)
- `source` (only using body, ignoring delivered_as/channel)
- `conversation_rating` (only using rating, ignoring remark text)
- `teammates` (fetched but not analyzed)

### ❌ **NOT USED** (Available but ignored)
- `waiting_since`, `snoozed_until` → Customer wait time tracking
- `priority` → Priority handling metrics
- `read` → Admin attention tracking
- `sla_applied` → **MAJOR OPPORTUNITY** for SLA compliance analysis
- `first_contact_reply` → Response time SLA tracking
- `conversation_rating.remark` → Customer feedback text analysis
- `ai_agent.content_sources` → **MAJOR OPPORTUNITY** for article effectiveness
- `statistics.time_to_assignment` → Routing efficiency
- `statistics.median_time_to_reply` → Responsiveness metric
- `statistics.count_assignments` → Handoff/complexity tracking
- `teammates` → Multi-admin collaboration analysis
- `conversation_parts[].part_type` → Note vs comment distinction
- `conversation_parts[].attachments` → Attachment tracking
- `linked_objects` → Related tickets/articles

---

## 🚀 MAJOR OPPORTUNITIES

### 1. **SLA Compliance Analysis** 🔥
**Available:** `sla_applied.sla_name`, `sla_applied.sla_status`  
**Not Using:** Everything  
**Impact:** Track SLA hit/miss rates, identify policy issues  
**Effort:** Low - just add to reports

### 2. **Fin Content Effectiveness** 🔥
**Available:** `ai_agent.content_sources[]` (articles Fin used)  
**Not Using:** Everything  
**Impact:** Which articles help Fin resolve vs. escalate  
**Effort:** Medium - need article-level analysis

### 3. **Customer Feedback Text Analysis** 🔥
**Available:** `conversation_rating.remark` (customer comments on rating)  
**Not Using:** Everything  
**Impact:** Rich qualitative feedback on what went wrong/right  
**Effort:** Low - already have sentiment analysis

### 4. **Routing & Assignment Efficiency** 
**Available:** `statistics.time_to_assignment`, `statistics.count_assignments`  
**Not Using:** Everything  
**Impact:** Identify routing bottlenecks, reassignment patterns  
**Effort:** Low - add to metrics

### 5. **Multi-Channel Analysis**
**Available:** `source.delivered_as` (email vs. chat vs. mobile)  
**Not Using:** Everything  
**Impact:** Channel-specific performance metrics  
**Effort:** Low - add to segmentation

### 6. **Wait Time Tracking**
**Available:** `waiting_since`, `statistics.last_contact_reply_at`  
**Not Using:** Everything  
**Impact:** Customer wait time distribution, identify abandoned conversations  
**Effort:** Low - add to metrics

---

## 📋 ENRICHMENT SUMMARY

### What We Fetch from Intercom API:

1. **Search API** (initial fetch):
   - All top-level fields EXCEPT `conversation_parts`
   - Returns: ~50 conversations per API call

2. **Conversations.find(id)** (per-conversation enrichment) **[NEW!]**:
   - Adds: `conversation_parts` with full message history
   - Returns: Full conversation object
   - Cost: 1 API call per conversation

3. **Contacts.find(id)** (per-conversation enrichment):
   - Adds: Full contact details with custom_attributes
   - Returns: Contact object
   - Cost: 1 API call per conversation

4. **Contacts.list_attached_segments(id)** (per-conversation enrichment):
   - Adds: Customer segment membership
   - Returns: Segment list
   - Cost: 1 API call per conversation

### API Call Math:
- 50 conversations = **1 search + 50 conversation.find + 50 contact.find + 50 segments = 151 API calls**
- Rate limit: 83 operations per 10 seconds
- Time: ~20 seconds for 50 conversations

---

## 🔧 RECOMMENDED NEXT STEPS

### Quick Wins (High Impact, Low Effort):
1. ✅ **Add SLA tracking** → Show hit/miss rates in reports
2. ✅ **Use conversation_rating.remark** → Add customer feedback quotes
3. ✅ **Track priority conversations** → Highlight urgent issues
4. ✅ **Add channel breakdown** → source.delivered_as analysis

### Medium Effort:
5. ✅ **Fin content analysis** → Which articles help Fin succeed
6. ✅ **Routing efficiency** → time_to_assignment, count_assignments
7. ✅ **Wait time metrics** → waiting_since analysis

### Long-term:
8. ✅ **Attachment tracking** → conversation_parts[].attachments
9. ✅ **Multi-admin collaboration** → teammates analysis
10. ✅ **Linked objects** → Related ticket tracking

---

## 📊 KEY METRICS COMPARISON

| Metric | Data We Have | Data We're Using | Opportunity |
|--------|--------------|------------------|-------------|
| **Response Time** | time_to_admin_reply, first_contact_reply_at, median_time_to_reply | time_to_admin_reply only | Use median for better average |
| **Resolution Time** | time_to_first_close, time_to_last_close, created_at, updated_at | time_to_last_close only | Add first_close for initial resolution tracking |
| **FCR** | count_reopens, state | Both ✅ | Good coverage |
| **Escalations** | admin_assignee_id, conversation_parts, teammates | Keyword matching in text | Use admin metadata instead |
| **CSAT** | conversation_rating.rating, remark | Rating only | Add remark for context |
| **Fin Performance** | ai_agent.resolution_state, content_sources, last_answer_type | resolution_state only | Add content effectiveness |
| **SLA** | sla_applied.sla_status | Not using ❌ | Major gap |
| **Wait Time** | waiting_since, last_contact_reply_at | Not using ❌ | Customer experience gap |

---

**Generated:** 2025-11-03  
**Next Review:** After conversation_parts enrichment validation

