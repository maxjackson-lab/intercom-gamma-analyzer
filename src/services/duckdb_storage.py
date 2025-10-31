"""
DuckDB Storage Service for Intercom Analysis Tool.
Provides analytical database with optimized performance for conversation analysis.
"""

import duckdb
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, date
import pandas as pd

logger = logging.getLogger(__name__)


class DuckDBStorage:
    """DuckDB-based storage for analytical queries."""
    
    def __init__(self, db_path: str = "conversations.duckdb"):
        self.db_path = Path(db_path)
        self.conn = None
        self._schema_initialized = False
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize DuckDB connection and create schema."""
        try:
            self.conn = duckdb.connect(str(self.db_path))
            self._create_schema()
            self._schema_initialized = True
            logger.info(f"DuckDB initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB: {e}")
            raise
    
    def ensure_schema(self):
        """
        Ensure schema is initialized before any operations.
        
        This is called by services that depend on specific tables being present.
        """
        if not self._schema_initialized:
            self._create_schema()
            self._schema_initialized = True
    
    def _create_schema(self):
        """Create analytical schema for conversations."""
        schema_sql = """
        -- Raw conversations table
        CREATE TABLE IF NOT EXISTS conversations (
            id VARCHAR PRIMARY KEY,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            state VARCHAR,
            priority VARCHAR,
            admin_assignee_id VARCHAR,
            language VARCHAR,
            conversation_rating INTEGER,
            time_to_admin_reply INTEGER,
            handling_time INTEGER,
            count_conversation_parts INTEGER,
            count_reopens INTEGER,
            ai_agent_participated BOOLEAN,
            fin_ai_preview BOOLEAN,
            copilot_used BOOLEAN,
            full_text TEXT,
            customer_messages TEXT,
            admin_messages TEXT,
            metadata JSON,
            confidence FLOAT DEFAULT 1.0,
            method VARCHAR DEFAULT 'tagged'
        );
        
        -- Tags table (normalized)
        CREATE TABLE IF NOT EXISTS conversation_tags (
            conversation_id VARCHAR,
            tag_name VARCHAR,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
        
        -- Topics table (normalized)
        CREATE TABLE IF NOT EXISTS conversation_topics (
            conversation_id VARCHAR,
            topic_name VARCHAR,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
        
        -- Categories table (from taxonomy)
        CREATE TABLE IF NOT EXISTS conversation_categories (
            conversation_id VARCHAR,
            primary_category VARCHAR,
            subcategory VARCHAR,
            confidence FLOAT,
            method VARCHAR,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
        
        -- Technical patterns table
        CREATE TABLE IF NOT EXISTS technical_patterns (
            conversation_id VARCHAR,
            pattern_type VARCHAR,
            pattern_value BOOLEAN,
            detected_keywords TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
        
        -- Escalations table
        CREATE TABLE IF NOT EXISTS escalations (
            conversation_id VARCHAR,
            escalated_to VARCHAR,
            escalation_notes TEXT,
            escalation_type VARCHAR,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
        
        -- Canny posts table
        CREATE TABLE IF NOT EXISTS canny_posts (
            id VARCHAR PRIMARY KEY,
            title TEXT,
            details TEXT,
            board_id VARCHAR,
            board_name VARCHAR,
            author_name VARCHAR,
            author_email VARCHAR,
            category VARCHAR,
            created_at TIMESTAMP,
            status VARCHAR,
            score INTEGER,
            comment_count INTEGER,
            url VARCHAR,
            sentiment VARCHAR,
            sentiment_confidence FLOAT,
            sentiment_source VARCHAR,
            engagement_score FLOAT,
            vote_velocity FLOAT,
            comment_velocity FLOAT,
            is_trending BOOLEAN,
            tags JSON
        );
        
        -- Canny comments table
        CREATE TABLE IF NOT EXISTS canny_comments (
            id VARCHAR PRIMARY KEY,
            post_id VARCHAR,
            author_name VARCHAR,
            author_email VARCHAR,
            value TEXT,
            created_at TIMESTAMP,
            sentiment VARCHAR,
            sentiment_confidence FLOAT,
            FOREIGN KEY (post_id) REFERENCES canny_posts(id)
        );
        
        -- Canny votes table
        CREATE TABLE IF NOT EXISTS canny_votes (
            id VARCHAR PRIMARY KEY,
            post_id VARCHAR,
            voter_name VARCHAR,
            voter_email VARCHAR,
            created_at TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES canny_posts(id)
        );
        
        -- Canny weekly snapshots table
        CREATE TABLE IF NOT EXISTS canny_weekly_snapshots (
            snapshot_date DATE PRIMARY KEY,
            total_posts INTEGER,
            open_posts INTEGER,
            planned_posts INTEGER,
            in_progress_posts INTEGER,
            completed_posts INTEGER,
            closed_posts INTEGER,
            total_votes INTEGER,
            total_comments INTEGER,
            sentiment_breakdown JSON,
            top_requests JSON,
            engagement_trends JSON
        );
        
        -- Admin profiles cache for agent performance tracking
        CREATE TABLE IF NOT EXISTS admin_profiles (
            admin_id VARCHAR PRIMARY KEY,
            name VARCHAR,
            email VARCHAR,
            public_email VARCHAR,
            vendor VARCHAR,
            active BOOLEAN,
            first_seen TIMESTAMP,
            last_updated TIMESTAMP
        );
        
        -- Individual agent performance snapshots
        CREATE TABLE IF NOT EXISTS agent_performance_history (
            snapshot_id VARCHAR PRIMARY KEY,
            analysis_date DATE,
            agent_id VARCHAR,
            agent_name VARCHAR,
            agent_email VARCHAR,
            vendor VARCHAR,
            total_conversations INTEGER,
            fcr_rate FLOAT,
            reopen_rate FLOAT,
            escalation_rate FLOAT,
            median_resolution_hours FLOAT,
            median_response_hours FLOAT,
            over_48h_count INTEGER,
            avg_conversation_complexity FLOAT,
            strong_categories JSON,
            weak_categories JSON,
            strong_subcategories JSON,
            weak_subcategories JSON,
            coaching_priority VARCHAR,
            performance_by_category JSON,
            performance_by_subcategory JSON,
            metadata JSON,
            FOREIGN KEY (agent_id) REFERENCES admin_profiles(admin_id)
        );
        
        -- Vendor-level performance snapshots
        CREATE TABLE IF NOT EXISTS vendor_performance_history (
            snapshot_id VARCHAR PRIMARY KEY,
            analysis_date DATE,
            vendor_name VARCHAR,
            team_fcr_rate FLOAT,
            team_escalation_rate FLOAT,
            total_agents INTEGER,
            total_conversations INTEGER,
            team_strengths JSON,
            team_weaknesses JSON,
            highlights JSON,
            lowlights JSON,
            metadata JSON
        );
        
        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
        CREATE INDEX IF NOT EXISTS idx_conversations_state ON conversations(state);
        CREATE INDEX IF NOT EXISTS idx_conversations_admin_assignee ON conversations(admin_assignee_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_ai_agent ON conversations(ai_agent_participated);
        CREATE INDEX IF NOT EXISTS idx_categories_primary ON conversation_categories(primary_category);
        CREATE INDEX IF NOT EXISTS idx_categories_subcategory ON conversation_categories(subcategory);
        CREATE INDEX IF NOT EXISTS idx_patterns_type ON technical_patterns(pattern_type);
        CREATE INDEX IF NOT EXISTS idx_escalations_to ON escalations(escalated_to);
        
        -- Canny indexes
        CREATE INDEX IF NOT EXISTS idx_canny_posts_created_at ON canny_posts(created_at);
        CREATE INDEX IF NOT EXISTS idx_canny_posts_status ON canny_posts(status);
        CREATE INDEX IF NOT EXISTS idx_canny_posts_board ON canny_posts(board_id);
        CREATE INDEX IF NOT EXISTS idx_canny_posts_sentiment ON canny_posts(sentiment);
        CREATE INDEX IF NOT EXISTS idx_canny_posts_engagement ON canny_posts(engagement_score);
        CREATE INDEX IF NOT EXISTS idx_canny_comments_post ON canny_comments(post_id);
        CREATE INDEX IF NOT EXISTS idx_canny_votes_post ON canny_votes(post_id);
        """
        
        self.conn.execute(schema_sql)
        logger.info("Database schema created successfully")
    
    def store_conversations(self, conversations: List[Dict], batch_size: int = 1000):
        """Store conversations in DuckDB with full text extraction."""
        logger.info(f"Storing {len(conversations)} conversations in DuckDB")
        
        # Process conversations in batches
        for i in range(0, len(conversations), batch_size):
            batch = conversations[i:i + batch_size]
            self._store_batch(batch)
        
        logger.info("All conversations stored successfully")
    
    def _store_batch(self, conversations: List[Dict]):
        """Store a batch of conversations."""
        conversation_data = []
        tag_data = []
        topic_data = []
        category_data = []
        pattern_data = []
        escalation_data = []
        
        for conv in conversations:
            # Extract basic conversation data
            conv_row = self._extract_conversation_data(conv)
            conversation_data.append(conv_row)
            
            # Extract tags
            tags = self._extract_tags(conv)
            for tag in tags:
                tag_data.append({
                    'conversation_id': conv['id'],
                    'tag_name': tag
                })
            
            # Extract topics
            topics = self._extract_topics(conv)
            for topic in topics:
                topic_data.append({
                    'conversation_id': conv['id'],
                    'topic_name': topic
                })
            
            # Extract categories (from taxonomy)
            categories = self._extract_categories(conv)
            for category in categories:
                category_data.append({
                    'conversation_id': conv['id'],
                    'primary_category': category['primary'],
                    'subcategory': category['subcategory'],
                    'confidence': category['confidence'],
                    'method': category['method']
                })
            
            # Extract technical patterns
            patterns = self._extract_technical_patterns(conv)
            for pattern in patterns:
                pattern_data.append({
                    'conversation_id': conv['id'],
                    'pattern_type': pattern['type'],
                    'pattern_value': pattern['value'],
                    'detected_keywords': pattern['keywords']
                })
            
            # Extract escalations
            escalations = self._extract_escalations(conv)
            for escalation in escalations:
                escalation_data.append({
                    'conversation_id': conv['id'],
                    'escalated_to': escalation['to'],
                    'escalation_notes': escalation['notes'],
                    'escalation_type': escalation['type']
                })
        
        # Insert data into tables
        if conversation_data:
            self._insert_conversations(conversation_data)
        if tag_data:
            self._insert_tags(tag_data)
        if topic_data:
            self._insert_topics(topic_data)
        if category_data:
            self._insert_categories(category_data)
        if pattern_data:
            self._insert_patterns(pattern_data)
        if escalation_data:
            self._insert_escalations(escalation_data)
    
    def _extract_conversation_data(self, conv: Dict) -> Dict:
        """Extract basic conversation data."""
        # Extract full conversation text
        full_text = self._extract_full_text(conv)
        customer_messages, admin_messages = self._extract_messages(conv)
        
        return {
            'id': conv.get('id'),
            'created_at': self._parse_timestamp(conv.get('created_at')),
            'updated_at': self._parse_timestamp(conv.get('updated_at')),
            'state': conv.get('state'),
            'priority': conv.get('priority'),
            'admin_assignee_id': conv.get('admin_assignee_id'),
            'language': conv.get('custom_attributes', {}).get('Language', ''),
            'conversation_rating': conv.get('conversation_rating'),
            'time_to_admin_reply': conv.get('statistics', {}).get('time_to_admin_reply'),
            'handling_time': conv.get('statistics', {}).get('handling_time'),
            'count_conversation_parts': conv.get('statistics', {}).get('count_conversation_parts'),
            'count_reopens': conv.get('statistics', {}).get('count_reopens'),
            'ai_agent_participated': conv.get('ai_agent_participated', False),
            'fin_ai_preview': conv.get('custom_attributes', {}).get('Fin AI Agent: Preview', False),
            'copilot_used': conv.get('custom_attributes', {}).get('Copilot used', False),
            'full_text': full_text,
            'customer_messages': customer_messages,
            'admin_messages': admin_messages,
            'metadata': json.dumps(conv.get('custom_attributes', {})),
            'confidence': 1.0,  # Default for tagged conversations
            'method': 'tagged'
        }
    
    def _extract_full_text(self, conv: Dict) -> str:
        """Extract full conversation text using utility function."""
        from src.utils.conversation_utils import extract_conversation_text
        return extract_conversation_text(conv, clean_html=True)
    
    def _extract_messages(self, conv: Dict) -> tuple:
        """Extract customer and admin messages separately using utility functions."""
        from src.utils.conversation_utils import extract_customer_messages
        
        # Use utility function for customer messages
        customer_msgs_list = extract_customer_messages(conv, clean_html=True)
        customer_messages = '\n\n'.join(customer_msgs_list) if customer_msgs_list else ''
        
        # Extract admin messages manually (no utility function for admin-specific messages yet)
        admin_messages = []
        
        # Check source for admin message
        source = conv.get('source', {})
        if source.get('author', {}).get('type') == 'admin':
            body = source.get('body', '').strip()
            if body:
                admin_messages.append(self._clean_html(body))
        
        # Check conversation parts for admin messages
        conversation_parts = conv.get('conversation_parts', {})
        if isinstance(conversation_parts, dict):
            parts = conversation_parts.get('conversation_parts', [])
        elif isinstance(conversation_parts, list):
            parts = conversation_parts
        else:
            parts = []
        
        for part in parts:
            if isinstance(part, dict):
                author = part.get('author', {})
                if author.get('type') == 'admin':
                    body = part.get('body', '').strip()
                    if body:
                        admin_messages.append(self._clean_html(body))
        
        return customer_messages, '\n\n'.join(admin_messages)
    
    def _clean_html(self, text: str) -> str:
        """Clean HTML from text."""
        if not text:
            return ""
        
        # Simple HTML cleaning - remove tags
        import re
        clean_text = re.sub(r'<[^>]+>', '', text)
        clean_text = re.sub(r'&nbsp;', ' ', clean_text)
        clean_text = re.sub(r'&amp;', '&', clean_text)
        clean_text = re.sub(r'&lt;', '<', clean_text)
        clean_text = re.sub(r'&gt;', '>', clean_text)
        
        return clean_text.strip()
    
    def _extract_tags(self, conv: Dict) -> List[str]:
        """Extract tags from conversation."""
        tags = []
        tags_data = conv.get('tags', {}).get('tags', [])
        
        for tag in tags_data:
            if isinstance(tag, dict):
                tags.append(tag.get('name', str(tag)))
            else:
                tags.append(str(tag))
        
        return tags
    
    def _extract_topics(self, conv: Dict) -> List[str]:
        """Extract topics from conversation."""
        topics = []
        topics_data = conv.get('topics', {}).get('topics', [])
        
        for topic in topics_data:
            if isinstance(topic, dict):
                topics.append(topic.get('name', str(topic)))
            else:
                topics.append(str(topic))
        
        return topics
    
    def _extract_categories(self, conv: Dict) -> List[Dict]:
        """Extract categories based on taxonomy."""
        categories = []
        
        # Get tags and topics
        tags = self._extract_tags(conv)
        topics = self._extract_topics(conv)
        
        # Map to taxonomy categories
        for tag in tags:
            category = self._map_tag_to_category(tag)
            if category:
                categories.append({
                    'primary': category['primary'],
                    'subcategory': category['subcategory'],
                    'confidence': 1.0,
                    'method': 'tagged'
                })
        
        for topic in topics:
            category = self._map_topic_to_category(topic)
            if category:
                categories.append({
                    'primary': category['primary'],
                    'subcategory': category['subcategory'],
                    'confidence': 1.0,
                    'method': 'tagged'
                })
        
        return categories
    
    def _map_tag_to_category(self, tag: str) -> Optional[Dict]:
        """Map tag to taxonomy category."""
        # Simple mapping - will be enhanced with full taxonomy
        tag_lower = tag.lower()
        
        if 'refund' in tag_lower or 'billing' in tag_lower:
            return {'primary': 'Billing', 'subcategory': 'Refund'}
        elif 'bug' in tag_lower or 'error' in tag_lower:
            return {'primary': 'Bug', 'subcategory': 'General'}
        elif 'account' in tag_lower:
            return {'primary': 'Account', 'subcategory': 'General'}
        elif 'dc' in tag_lower:
            return {'primary': 'Custom', 'subcategory': 'DC'}
        
        return None
    
    def _map_topic_to_category(self, topic: str) -> Optional[Dict]:
        """Map topic to taxonomy category."""
        # Simple mapping - will be enhanced with full taxonomy
        topic_lower = topic.lower()
        
        if topic_lower in ['refund', 'billing', 'invoice', 'payment']:
            return {'primary': 'Billing', 'subcategory': topic.title()}
        elif topic_lower in ['export', 'ppt', 'pdf', 'slides']:
            return {'primary': 'Bug', 'subcategory': 'Export'}
        elif topic_lower in ['domain', 'publish', 'site']:
            return {'primary': 'Sites', 'subcategory': topic.title()}
        elif topic_lower == 'api':
            return {'primary': 'API', 'subcategory': 'General'}
        
        return None
    
    def _extract_technical_patterns(self, conv: Dict) -> List[Dict]:
        """Extract technical troubleshooting patterns."""
        patterns = []
        full_text = self._extract_full_text(conv)
        text_lower = full_text.lower()
        
        # Cache clearing patterns
        cache_patterns = ['clear cache', 'clear cookies', 'ctrl+shift+delete', 'hard refresh']
        if any(pattern in text_lower for pattern in cache_patterns):
            patterns.append({
                'type': 'cache_clear',
                'value': True,
                'keywords': ', '.join([p for p in cache_patterns if p in text_lower])
            })
        
        # Browser switching patterns
        browser_patterns = ['different browser', 'try chrome', 'try firefox', 'incognito']
        if any(pattern in text_lower for pattern in browser_patterns):
            patterns.append({
                'type': 'browser_switch',
                'value': True,
                'keywords': ', '.join([p for p in browser_patterns if p in text_lower])
            })
        
        # Connection issues
        connection_patterns = ['internet connection', 'wifi', 'network', 'connection issue']
        if any(pattern in text_lower for pattern in connection_patterns):
            patterns.append({
                'type': 'connection_issue',
                'value': True,
                'keywords': ', '.join([p for p in connection_patterns if p in text_lower])
            })
        
        return patterns
    
    def _extract_escalations(self, conv: Dict) -> List[Dict]:
        """Extract escalation patterns."""
        escalations = []
        full_text = self._extract_full_text(conv)
        text_lower = full_text.lower()
        
        # Look for specific names
        names = ['dae-ho', 'hilary', 'max', 'max jackson']
        for name in names:
            if name in text_lower:
                escalations.append({
                    'to': name.title(),
                    'notes': self._extract_escalation_notes(full_text, name),
                    'type': 'mention'
                })
        
        return escalations
    
    def _extract_escalation_notes(self, text: str, name: str) -> str:
        """Extract escalation notes around a name mention."""
        import re
        
        # Find sentences containing the name
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            if name.lower() in sentence.lower():
                return sentence.strip()[:200]  # Limit length
        
        return ""
    
    def _parse_timestamp(self, timestamp) -> Optional[datetime]:
        """Parse timestamp to datetime."""
        if not timestamp:
            return None
        
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp)
        
        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                return None
        
        return None
    
    def _insert_conversations(self, data: List[Dict]):
        """Insert conversation data."""
        df = pd.DataFrame(data)
        self.conn.execute("INSERT OR REPLACE INTO conversations SELECT * FROM df", {"df": df})
    
    def _insert_tags(self, data: List[Dict]):
        """Insert tag data."""
        df = pd.DataFrame(data)
        self.conn.execute("INSERT OR REPLACE INTO conversation_tags SELECT * FROM df", {"df": df})
    
    def _insert_topics(self, data: List[Dict]):
        """Insert topic data."""
        df = pd.DataFrame(data)
        self.conn.execute("INSERT OR REPLACE INTO conversation_topics SELECT * FROM df", {"df": df})
    
    def _insert_categories(self, data: List[Dict]):
        """Insert category data."""
        df = pd.DataFrame(data)
        self.conn.execute("INSERT OR REPLACE INTO conversation_categories SELECT * FROM df", {"df": df})
    
    def _insert_patterns(self, data: List[Dict]):
        """Insert pattern data."""
        df = pd.DataFrame(data)
        self.conn.execute("INSERT OR REPLACE INTO technical_patterns SELECT * FROM df", {"df": df})
    
    def _insert_escalations(self, data: List[Dict]):
        """Insert escalation data."""
        df = pd.DataFrame(data)
        self.conn.execute("INSERT OR REPLACE INTO escalations SELECT * FROM df", {"df": df})
    
    def query(self, sql: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """Execute analytical query and return DataFrame."""
        try:
            if params:
                return self.conn.execute(sql, params).df()
            else:
                return self.conn.execute(sql).df()
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    def get_conversations_by_category(self, category: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Get conversations by category and date range."""
        sql = """
        SELECT c.*, cc.subcategory, cc.confidence, cc.method
        FROM conversations c
        JOIN conversation_categories cc ON c.id = cc.conversation_id
        WHERE cc.primary_category = $category
        AND c.created_at >= $start_date
        AND c.created_at <= $end_date
        ORDER BY c.created_at DESC
        """

        return self.query(sql, {
            'category': category,
            'start_date': start_date,
            'end_date': end_date
        })
    
    def get_technical_patterns(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get technical patterns in date range."""
        sql = """
        SELECT
            tp.pattern_type,
            COUNT(*) as occurrence_count,
            COUNT(DISTINCT tp.conversation_id) as unique_conversations,
            STRING_AGG(DISTINCT tp.detected_keywords, ', ') as keywords
        FROM technical_patterns tp
        JOIN conversations c ON tp.conversation_id = c.id
        WHERE c.created_at >= $start_date
        AND c.created_at <= $end_date
        AND tp.pattern_value = true
        GROUP BY tp.pattern_type
        ORDER BY occurrence_count DESC
        """

        return self.query(sql, {
            'start_date': start_date,
            'end_date': end_date
        })
    
    def get_escalations(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get escalation patterns in date range."""
        sql = """
        SELECT
            e.escalated_to,
            COUNT(*) as escalation_count,
            AVG(c.handling_time) as avg_handling_time,
            STRING_AGG(DISTINCT e.escalation_notes, ' | ') as sample_notes
        FROM escalations e
        JOIN conversations c ON e.conversation_id = c.id
        WHERE c.created_at >= $start_date
        AND c.created_at <= $end_date
        GROUP BY e.escalated_to
        ORDER BY escalation_count DESC
        """

        return self.query(sql, {
            'start_date': start_date,
            'end_date': end_date
        })
    
    def get_fin_analysis(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get Fin AI analysis in date range."""
        sql = """
        SELECT
            CASE
                WHEN ai_agent_participated THEN 'Fin Handled'
                ELSE 'Human Only'
            END as interaction_type,
            COUNT(*) as conversation_count,
            AVG(handling_time) as avg_handling_time,
            AVG(conversation_rating) as avg_rating,
            COUNT(CASE WHEN state = 'closed' THEN 1 END) as resolved_count
        FROM conversations
        WHERE created_at >= $start_date
        AND created_at <= $end_date
        GROUP BY ai_agent_participated
        """

        return self.query(sql, {
            'start_date': start_date,
            'end_date': end_date
        })
    
    def store_canny_posts(self, posts: List[Dict], batch_size: int = 100):
        """Store Canny posts in DuckDB."""
        logger.info(f"Storing {len(posts)} Canny posts in DuckDB")
        
        for i in range(0, len(posts), batch_size):
            batch = posts[i:i + batch_size]
            self._store_canny_batch(batch)
        
        logger.info("All Canny posts stored successfully")
    
    def _store_canny_batch(self, posts: List[Dict]):
        """Store a batch of Canny posts."""
        post_data = []
        comment_data = []
        vote_data = []
        
        for post in posts:
            # Extract post data
            post_row = self._extract_canny_post_data(post)
            post_data.append(post_row)
            
            # Extract comments
            comments = post.get('comments', [])
            for comment in comments:
                comment_row = self._extract_canny_comment_data(comment, post['id'])
                comment_data.append(comment_row)
            
            # Extract votes
            votes = post.get('votes', [])
            for vote in votes:
                vote_row = self._extract_canny_vote_data(vote, post['id'])
                vote_data.append(vote_row)
        
        # Insert data
        if post_data:
            self._insert_canny_posts(post_data)
        if comment_data:
            self._insert_canny_comments(comment_data)
        if vote_data:
            self._insert_canny_votes(vote_data)
    
    def _extract_canny_post_data(self, post: Dict) -> Dict:
        """Extract Canny post data for storage."""
        sentiment_analysis = post.get('sentiment_analysis', {})
        
        return {
            'id': post.get('id'),
            'title': post.get('title', ''),
            'details': post.get('details', ''),
            'board_id': post.get('board', {}).get('id'),
            'board_name': post.get('board', {}).get('name', ''),
            'author_name': post.get('author', {}).get('name', ''),
            'author_email': post.get('author', {}).get('email'),
            'category': post.get('category'),
            'created_at': post.get('created'),
            'status': post.get('status', 'open'),
            'score': post.get('score', 0),
            'comment_count': post.get('commentCount', 0),
            'url': post.get('url', ''),
            'sentiment': sentiment_analysis.get('sentiment'),
            'sentiment_confidence': sentiment_analysis.get('confidence'),
            'sentiment_source': sentiment_analysis.get('model'),
            'engagement_score': post.get('engagement_score', 0),
            'vote_velocity': post.get('vote_velocity', 0),
            'comment_velocity': post.get('comment_velocity', 0),
            'is_trending': post.get('is_trending', False),
            'tags': json.dumps(post.get('tags', []))
        }
    
    def _extract_canny_comment_data(self, comment: Dict, post_id: str) -> Dict:
        """Extract Canny comment data for storage."""
        return {
            'id': comment.get('id'),
            'post_id': post_id,
            'author_name': comment.get('author', {}).get('name', ''),
            'author_email': comment.get('author', {}).get('email'),
            'value': comment.get('value', ''),
            'created_at': comment.get('created'),
            'sentiment': None,  # Will be filled by analyzer
            'sentiment_confidence': None
        }
    
    def _extract_canny_vote_data(self, vote: Dict, post_id: str) -> Dict:
        """Extract Canny vote data for storage."""
        return {
            'id': vote.get('id'),
            'post_id': post_id,
            'voter_name': vote.get('voter', {}).get('name', ''),
            'voter_email': vote.get('voter', {}).get('email'),
            'created_at': vote.get('created')
        }
    
    def _insert_canny_posts(self, posts: List[Dict]):
        """Insert Canny posts into database."""
        if not posts:
            return
        
        df = pd.DataFrame(posts)
        self.conn.execute("INSERT OR REPLACE INTO canny_posts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                         df.values.tolist())
    
    def _insert_canny_comments(self, comments: List[Dict]):
        """Insert Canny comments into database."""
        if not comments:
            return
        
        df = pd.DataFrame(comments)
        self.conn.execute("INSERT OR REPLACE INTO canny_comments VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                         df.values.tolist())
    
    def _insert_canny_votes(self, votes: List[Dict]):
        """Insert Canny votes into database."""
        if not votes:
            return
        
        df = pd.DataFrame(votes)
        self.conn.execute("INSERT OR REPLACE INTO canny_votes VALUES (?, ?, ?, ?, ?)", 
                         df.values.tolist())
    
    def store_canny_weekly_snapshot(self, snapshot_data: Dict):
        """Store weekly Canny snapshot."""
        sql = """
        INSERT OR REPLACE INTO canny_weekly_snapshots 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        self.conn.execute(sql, [
            snapshot_data['snapshot_date'],
            snapshot_data['total_posts'],
            snapshot_data['open_posts'],
            snapshot_data['planned_posts'],
            snapshot_data['in_progress_posts'],
            snapshot_data['completed_posts'],
            snapshot_data['closed_posts'],
            snapshot_data['total_votes'],
            snapshot_data['total_comments'],
            json.dumps(snapshot_data['sentiment_breakdown']),
            json.dumps(snapshot_data['top_requests']),
            json.dumps(snapshot_data['engagement_trends'])
        ])
    
    def get_canny_posts_by_date_range(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get Canny posts in date range."""
        sql = """
        SELECT * FROM canny_posts
        WHERE created_at >= $start_date AND created_at <= $end_date
        ORDER BY created_at DESC
        """

        return self.query(sql, {
            'start_date': start_date,
            'end_date': end_date
        })
    
    def get_canny_sentiment_breakdown(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get Canny sentiment breakdown by status and category."""
        sql = """
        SELECT
            status,
            category,
            sentiment,
            COUNT(*) as count,
            AVG(sentiment_confidence) as avg_confidence,
            AVG(engagement_score) as avg_engagement
        FROM canny_posts
        WHERE created_at >= $start_date AND created_at <= $end_date
        AND sentiment IS NOT NULL
        GROUP BY status, category, sentiment
        ORDER BY count DESC
        """

        return self.query(sql, {
            'start_date': start_date,
            'end_date': end_date
        })
    
    def get_canny_trending_posts(self, start_date: date, end_date: date, limit: int = 10) -> pd.DataFrame:
        """Get trending Canny posts."""
        sql = """
        SELECT
            id, title, score, comment_count, engagement_score,
            vote_velocity, comment_velocity, sentiment, status, url
        FROM canny_posts
        WHERE created_at >= $start_date AND created_at <= $end_date
        AND is_trending = true
        ORDER BY engagement_score DESC
        LIMIT $limit
        """

        return self.query(sql, {
            'start_date': start_date,
            'end_date': end_date,
            'limit': limit
        })
    
    def get_canny_trends(self, weeks: int = 4) -> Dict:
        """
        Get Canny trends over specified number of weeks.
        
        Args:
            weeks: Number of weeks to analyze
            
        Returns:
            Dictionary with trend data including week-over-week changes
        """
        sql = """
        SELECT 
            snapshot_date,
            total_posts,
            open_posts,
            planned_posts,
            in_progress_posts,
            completed_posts,
            closed_posts,
            total_votes,
            total_comments,
            sentiment_breakdown,
            top_requests,
            engagement_trends
        FROM canny_weekly_snapshots
        ORDER BY snapshot_date DESC
        LIMIT ?
        """
        
        try:
            result = self.conn.execute(sql, [weeks]).fetchall()
            
            if not result:
                return {
                    'weeks_analyzed': 0,
                    'snapshots': [],
                    'trends': {},
                    'message': 'No historical data available'
                }
            
            snapshots = []
            for row in result:
                snapshots.append({
                    'snapshot_date': row[0],
                    'total_posts': row[1],
                    'open_posts': row[2],
                    'planned_posts': row[3],
                    'in_progress_posts': row[4],
                    'completed_posts': row[5],
                    'closed_posts': row[6],
                    'total_votes': row[7],
                    'total_comments': row[8],
                    'sentiment_breakdown': json.loads(row[9]) if row[9] else {},
                    'top_requests': json.loads(row[10]) if row[10] else [],
                    'engagement_trends': json.loads(row[11]) if row[11] else {}
                })
            
            # Calculate week-over-week trends
            trends = {}
            if len(snapshots) >= 2:
                latest = snapshots[0]
                previous = snapshots[1]
                
                trends = {
                    'total_posts_change': latest['total_posts'] - previous['total_posts'],
                    'total_posts_change_pct': self._calculate_percentage_change(
                        previous['total_posts'], latest['total_posts']
                    ),
                    'votes_change': latest['total_votes'] - previous['total_votes'],
                    'votes_change_pct': self._calculate_percentage_change(
                        previous['total_votes'], latest['total_votes']
                    ),
                    'comments_change': latest['total_comments'] - previous['total_comments'],
                    'comments_change_pct': self._calculate_percentage_change(
                        previous['total_comments'], latest['total_comments']
                    ),
                    'open_posts_change': latest['open_posts'] - previous['open_posts'],
                    'completed_posts_change': latest['completed_posts'] - previous['completed_posts'],
                }
            
            return {
                'weeks_analyzed': len(snapshots),
                'snapshots': snapshots,
                'trends': trends,
                'latest_snapshot': snapshots[0] if snapshots else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get Canny trends: {e}")
            return {
                'weeks_analyzed': 0,
                'snapshots': [],
                'trends': {},
                'error': str(e)
            }
    
    def _calculate_percentage_change(self, old_value: int, new_value: int) -> float:
        """Calculate percentage change between two values."""
        if old_value == 0:
            return 100.0 if new_value > 0 else 0.0
        return round(((new_value - old_value) / old_value) * 100, 2)
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("DuckDB connection closed")






