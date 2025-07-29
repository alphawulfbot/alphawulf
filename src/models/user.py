"""
Comprehensive User Model for Alpha Wulf
Handles all database operations with proper type conversion and error handling
Compatible with Supabase PostgreSQL database
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class User:
    """User model with comprehensive database operations"""
    
    def __init__(self, telegram_id: int, username: str = '', first_name: str = '', last_name: str = ''):
        self.telegram_id = int(telegram_id)
        self.username = username or ''
        self.first_name = first_name or ''
        self.last_name = last_name or ''
        
        # Game attributes with default values
        self.coins = 2500
        self.energy = 100
        self.max_energy = 100
        self.tap_power = 1
        self.energy_regen_rate = 1
        self.last_energy_update = datetime.now()
        
        # Additional attributes
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
    @staticmethod
    def get_db_connection():
        """Get database connection with proper error handling"""
        try:
            # Use environment variable for database URL
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                logger.error("DATABASE_URL environment variable not set")
                return None
                
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    @classmethod
    def get_by_telegram_id(cls, telegram_id: int):
        """Get user by telegram ID with proper error handling"""
        try:
            conn = cls.get_db_connection()
            if not conn:
                return None
                
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM users WHERE telegram_id = %s
                """, (int(telegram_id),))
                
                row = cursor.fetchone()
                if row:
                    user = cls(
                        telegram_id=row['telegram_id'],
                        username=row.get('username', ''),
                        first_name=row.get('first_name', ''),
                        last_name=row.get('last_name', '')
                    )
                    
                    # Load game data with type conversion
                    user.coins = int(float(row.get('coins', 2500)))
                    user.energy = int(float(row.get('energy', 100)))
                    user.max_energy = int(float(row.get('max_energy', 100)))
                    user.tap_power = int(float(row.get('tap_power', 1)))
                    user.energy_regen_rate = int(float(row.get('energy_regen_rate', 1)))
                    
                    # Handle datetime fields
                    if row.get('last_energy_update'):
                        if isinstance(row['last_energy_update'], str):
                            user.last_energy_update = datetime.fromisoformat(row['last_energy_update'].replace('Z', '+00:00'))
                        else:
                            user.last_energy_update = row['last_energy_update']
                    
                    if row.get('created_at'):
                        if isinstance(row['created_at'], str):
                            user.created_at = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
                        else:
                            user.created_at = row['created_at']
                    
                    if row.get('updated_at'):
                        if isinstance(row['updated_at'], str):
                            user.updated_at = datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
                        else:
                            user.updated_at = row['updated_at']
                    
                    logger.info(f"User found: {telegram_id}")
                    return user
                else:
                    logger.info(f"User not found: {telegram_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting user {telegram_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def create_user(cls, telegram_id: int, username: str = '', first_name: str = '', last_name: str = ''):
        """Create new user with proper error handling"""
        try:
            conn = cls.get_db_connection()
            if not conn:
                return None
                
            user = cls(telegram_id, username, first_name, last_name)
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (
                        telegram_id, username, first_name, last_name,
                        coins, energy, max_energy, tap_power, energy_regen_rate,
                        last_energy_update, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    int(user.telegram_id),
                    user.username,
                    user.first_name,
                    user.last_name,
                    int(user.coins),
                    int(user.energy),
                    int(user.max_energy),
                    int(user.tap_power),
                    int(user.energy_regen_rate),
                    user.last_energy_update,
                    user.created_at,
                    user.updated_at
                ))
                
                conn.commit()
                logger.info(f"User created: {telegram_id}")
                return user
                
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def save(self):
        """Save user data with comprehensive error handling and type conversion"""
        try:
            conn = self.get_db_connection()
            if not conn:
                logger.error("Failed to get database connection")
                return False
                
            self.updated_at = datetime.now()
            
            with conn.cursor() as cursor:
                # Update user data with proper type conversion
                cursor.execute("""
                    UPDATE users SET
                        username = %s,
                        first_name = %s,
                        last_name = %s,
                        coins = %s,
                        energy = %s,
                        max_energy = %s,
                        tap_power = %s,
                        energy_regen_rate = %s,
                        last_energy_update = %s,
                        updated_at = %s
                    WHERE telegram_id = %s
                """, (
                    self.username,
                    self.first_name,
                    self.last_name,
                    int(float(self.coins)),  # Ensure integer conversion
                    int(float(self.energy)),
                    int(float(self.max_energy)),
                    int(float(self.tap_power)),
                    int(float(self.energy_regen_rate)),
                    self.last_energy_update,
                    self.updated_at,
                    int(self.telegram_id)
                ))
                
                conn.commit()
                logger.info(f"User saved successfully: {self.telegram_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving user {self.telegram_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def update_energy(self):
        """Update energy based on time elapsed with proper error handling"""
        try:
            now = datetime.now()
            time_diff = now - self.last_energy_update
            minutes_passed = time_diff.total_seconds() / 60
            
            # Regenerate energy (1 energy per 30 seconds = 2 energy per minute)
            energy_to_add = int(minutes_passed * 2)
            
            if energy_to_add > 0:
                self.energy = min(self.max_energy, self.energy + energy_to_add)
                self.last_energy_update = now
                logger.info(f"Energy updated for user {self.telegram_id}: +{energy_to_add} energy")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating energy for user {self.telegram_id}: {e}")
            return False
    
    def can_tap(self):
        """Check if user can tap (has energy)"""
        return self.energy > 0
    
    def tap(self, taps: int = 1):
        """Process tap with proper validation and error handling"""
        try:
            if not self.can_tap():
                return False, "No energy available"
            
            # Update energy first
            self.update_energy()
            
            # Process taps
            actual_taps = min(taps, self.energy)
            self.energy = max(0, self.energy - actual_taps)
            self.coins += actual_taps * self.tap_power
            
            # Save to database
            if self.save():
                logger.info(f"Tap processed for user {self.telegram_id}: {actual_taps} taps, {self.coins} total coins")
                return True, f"Tapped {actual_taps} times"
            else:
                return False, "Failed to save tap data"
                
        except Exception as e:
            logger.error(f"Error processing tap for user {self.telegram_id}: {e}")
            return False, f"Tap error: {str(e)}"
    
    def to_dict(self):
        """Convert user to dictionary with proper serialization"""
        try:
            return {
                'telegram_id': int(self.telegram_id),
                'username': self.username,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'coins': int(self.coins),
                'energy': int(self.energy),
                'max_energy': int(self.max_energy),
                'tap_power': int(self.tap_power),
                'energy_regen_rate': int(self.energy_regen_rate),
                'last_energy_update': self.last_energy_update.isoformat() if isinstance(self.last_energy_update, datetime) else str(self.last_energy_update),
                'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
                'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at)
            }
        except Exception as e:
            logger.error(f"Error converting user to dict: {e}")
            return {
                'telegram_id': int(self.telegram_id),
                'username': self.username,
                'first_name': self.first_name,
                'coins': 2500,
                'energy': 100,
                'max_energy': 100,
                'tap_power': 1,
                'energy_regen_rate': 1
            }

