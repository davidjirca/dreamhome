from typing import Optional, List, Dict, Any
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

from app.core.config import settings
from app.models.alerts import EmailLog
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID


class EmailService:
    """Service for sending emails with HTML templates"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAILS_FROM_EMAIL
        self.from_name = settings.EMAILS_FROM_NAME
        
        # Setup Jinja2 for email templates
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'emails')
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    def _is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return all([
            self.smtp_host,
            self.smtp_port,
            self.smtp_user,
            self.smtp_password,
            self.from_email
        ])
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        email_type: str = "general",
        user_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None,
        email_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an email and log the result
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text fallback (optional)
            email_type: Type of email for logging (e.g., 'new_listing', 'price_drop')
            user_id: User ID for logging (optional)
            db: Database session for logging (optional)
            email_metadata: Additional metadata to log (optional)
        
        Returns:
            True if email sent successfully, False otherwise
        """
        
        # Check if email is configured
        if not self._is_configured():
            print("⚠️  Email service not configured. Skipping email send.")
            print(f"   Would send: {email_type} to {to_email}")
            print(f"   Subject: {subject}")
            
            # Log to database even if not configured
            if db:
                await self._log_email(
                    db, to_email, email_type, subject,
                    success=False,
                    error_message="Email service not configured",
                    user_id=user_id,
                    email_metadata=email_metadata
                )
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Attach plain text version
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Attach HTML version
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ Email sent: {email_type} to {to_email}")
            
            # Log success
            if db:
                await self._log_email(
                    db, to_email, email_type, subject,
                    success=True,
                    user_id=user_id,
                    email_metadata=email_metadata
                )
            
            return True
            
        except Exception as e:
            print(f"❌ Email send failed: {e}")
            
            # Log failure
            if db:
                await self._log_email(
                    db, to_email, email_type, subject,
                    success=False,
                    error_message=str(e),
                    user_id=user_id,
                    email_metadata=email_metadata
                )
            
            return False
    
    async def _log_email(
        self,
        db: AsyncSession,
        to_email: str,
        email_type: str,
        subject: str,
        success: bool,
        error_message: Optional[str] = None,
        user_id: Optional[UUID] = None,
        email_metadata: Optional[Dict[str, Any]] = None
    ):
        """Log email send attempt to database"""
        try:
            email_log = EmailLog(
                user_id=user_id,
                email_to=to_email,
                email_type=email_type,
                subject=subject,
                success=success,
                error_message=error_message,
                email_metadata=email_metadata  # FIXED: was 'metadata'
            )
            db.add(email_log)
            await db.flush()
        except Exception as e:
            print(f"⚠️  Failed to log email: {e}")
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render an email template with context
        
        Args:
            template_name: Template file name (e.g., 'new_listing_alert.html')
            context: Template context variables
        
        Returns:
            Rendered HTML string
        """
        try:
            template = self.jinja_env.get_template(template_name)
            
            # Add common context variables
            context.update({
                'platform_name': 'dreamhome',
                'platform_url': 'https://dreamhome.ro',
                'current_year': datetime.now().year,
                'support_email': settings.EMAILS_FROM_EMAIL
            })
            
            return template.render(**context)
        except Exception as e:
            print(f"❌ Template rendering failed: {e}")
            raise
    
    async def send_welcome_email(
        self,
        to_email: str,
        user_name: str,
        user_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Send welcome email to new users"""
        context = {
            'user_name': user_name,
            'login_url': f'{settings.BACKEND_CORS_ORIGINS[0]}/login' if settings.BACKEND_CORS_ORIGINS else '#'
        }
        
        html_content = self.render_template('welcome.html', context)
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Welcome to dreamhome, {user_name}!",
            html_content=html_content,
            email_type='welcome',
            user_id=user_id,
            db=db
        )
    
    async def send_new_listing_alert(
        self,
        to_email: str,
        user_id: UUID,
        search_name: str,
        properties: List[Dict[str, Any]],
        search_url: str,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Send alert for new listings matching saved search"""
        context = {
            'search_name': search_name,
            'properties': properties,
            'property_count': len(properties),
            'search_url': search_url
        }
        
        html_content = self.render_template('new_listing_alert.html', context)
        
        return await self.send_email(
            to_email=to_email,
            subject=f"New Properties Match Your Search: {search_name}",
            html_content=html_content,
            email_type='new_listing_alert',
            user_id=user_id,
            db=db,
            email_metadata={
                'search_name': search_name,
                'property_count': len(properties),
                'property_ids': [p.get('id') for p in properties]
            }
        )
    
    async def send_price_drop_alert(
        self,
        to_email: str,
        user_id: UUID,
        property_title: str,
        old_price: float,
        new_price: float,
        price_drop_percent: float,
        property_url: str,
        main_photo: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Send alert for price drop on favorited property"""
        context = {
            'property_title': property_title,
            'old_price': old_price,
            'new_price': new_price,
            'price_drop': old_price - new_price,
            'price_drop_percent': abs(price_drop_percent),
            'property_url': property_url,
            'main_photo': main_photo
        }
        
        html_content = self.render_template('price_drop_alert.html', context)
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Price Drop Alert: {property_title}",
            html_content=html_content,
            email_type='price_drop_alert',
            user_id=user_id,
            db=db,
            email_metadata={
                'property_title': property_title,
                'old_price': float(old_price),
                'new_price': float(new_price),
                'price_drop_percent': float(price_drop_percent)
            }
        )
    
    async def send_daily_digest(
        self,
        to_email: str,
        user_id: UUID,
        saved_searches_with_new: List[Dict[str, Any]],
        price_drops: List[Dict[str, Any]],
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Send daily digest of new listings and price drops"""
        total_new = sum(s.get('new_count', 0) for s in saved_searches_with_new)
        
        context = {
            'saved_searches': saved_searches_with_new,
            'price_drops': price_drops,
            'total_new_listings': total_new,
            'total_price_drops': len(price_drops),
            'digest_date': datetime.now().strftime('%B %d, %Y')
        }
        
        html_content = self.render_template('daily_digest.html', context)
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Your Daily Property Digest - {total_new} New Listings",
            html_content=html_content,
            email_type='daily_digest',
            user_id=user_id,
            db=db,
            email_metadata={
                'total_new_listings': total_new,
                'total_price_drops': len(price_drops)
            }
        )


# Global email service instance
email_service = EmailService()