\
\
\
   
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, 
    ForeignKey, Text, Enum as SQLEnum, Numeric
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum
from datetime import date as _date

                                                                         
                                                        
                                                  
from services.holidays import calculate_working_days              

class UserRole(str, enum.Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    RECRUITER = "recruiter"

class DictionaryType(str, enum.Enum):
    SPECIALIST_LEVEL = "specialist_level"                           
    VACANCY_STATUS = "vacancy_status"                           
    IT_ROLE = "it_role"                                 
    PROJECT = "project"                                            
    SOURCE = "source"                                          
    EMPLOYMENT_TYPE = "employment_type"                       
    REPLACEMENT_TYPE = "replacement_type"                    
    FEASIBILITY = "feasibility"                             
    BLOCK = "block"                                  
    ADMIN_MANAGER = "admin_manager"                                           
    TEAM_LEAD = "team_lead"                            
    INTERNAL_TRANSFER = "internal_transfer"                        
    CITY = "city"                                            

class User(Base):
                                                         
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.RECRUITER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_temporary_password = Column(Boolean, default=True)
                                                                                
    totp_secret = Column(String(64), nullable=True)                           
    is_2fa_enabled = Column(Boolean, default=False)                             
                                                                                
                                                                                          
    is_vacancies_tour_completed = Column(Boolean, nullable=False, default=False)
    is_reports_tour_completed   = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
                   
    vacancies = relationship("Vacancy", back_populates="recruiter", foreign_keys="Vacancy.recruiter_id")

class Dictionary(Base):
                                                  
    __tablename__ = "dictionaries"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(DictionaryType), nullable=False, index=True)
    value = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Vacancy(Base):
\
\
       
    __tablename__ = "vacancies"
    
    id = Column(Integer, primary_key=True, index=True)
    
                                       
    vacancy_id = Column(String(50), nullable=True, index=True, comment="ID вакансии")
    
                             
    open_date = Column(Date, nullable=True, comment="Дата открытия")
    
                                  
    quantity = Column(Integer, default=1, comment="Кол-во вакансий")
    
                                         
    level_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    
                                          
    position_name = Column(String(255), nullable=False, comment="Вакансия")
    
                                     
    status_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    
                             
    it_role_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    
                                                   
    admin_manager_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    
                                             
    team_lead_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    
                                         
    project_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    
                                                                
    resume_at_customer = Column(Integer, default=0, comment="Передано заказчику")
    
                                                             
    resume_approved = Column(Integer, default=0, comment="Резюме одобрено")
    
                                                                        
    interviews_fact = Column(Integer, default=0, comment="Собеседования факт")
    interviews_plan = Column(Integer, default=0, comment="Собеседования план")
    
                                
    offer_made = Column(Integer, default=0, comment="Сделан оффер")
    
                                    
    city_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    city_text = Column(String(100), nullable=True, comment="Город выхода (текст)")
    
                                     
    source_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    
                                                                  
    internal_transfer_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    
                                       
    status_changed_at = Column(Date, nullable=True, comment="Дата изменения статуса")
    
                                       
    close_date = Column(Date, nullable=True, comment="Дата закрытия вакансии")
    
                                
    candidate_name = Column(String(255), nullable=True, comment="ФИО кандидата")
    
                                                            
    candidate_company = Column(String(255), nullable=True, comment="Компания кандидата")
    
                                   
    replacement_type_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    
                                                          
    ex_employee_name = Column(String(255), nullable=True, comment="ФИО бывшего сотрудника")
    
                        
    unit_id = Column(String(50), nullable=True, comment="ID ШЕ")
    
                                    
    employment_type_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    
                                  
    feasibility_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    
                                            
    iqhr_link = Column(String(500), nullable=True, comment="Ссылка на заявку IQHR")
    
                         
    recruiter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
                           
    block_id = Column(Integer, ForeignKey("dictionaries.id"), nullable=True)
    
                                                                                    
    hold_days = Column(Integer, default=0, comment="Дни в холде")
    
                                                        
    salary_gross = Column(Integer, nullable=True, comment="Зарплата кандидатов Gross")
    
                                                                               
    resumes_sent_cnt = Column(Integer, default=0, comment="Кол-во направленных резюме")
    candidates_agreed_cnt = Column(Integer, default=0, comment="Кол-во согласованных кандидатов")
    interviews_planned_cnt = Column(Integer, default=0, comment="Кол-во запланированных интервью")
    interviews_conducted_cnt = Column(Integer, default=0, comment="Кол-во проведенных интервью")
    
                                                                           
    counters_updated_at = Column(DateTime(timezone=True), nullable=True, comment="Когда последний раз обновлялись еженедельные счётчики")
    
                
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
                   
    recruiter = relationship("User", back_populates="vacancies", foreign_keys=[recruiter_id])
    level = relationship("Dictionary", foreign_keys=[level_id])
    status = relationship("Dictionary", foreign_keys=[status_id])
    it_role = relationship("Dictionary", foreign_keys=[it_role_id])
    admin_manager = relationship("Dictionary", foreign_keys=[admin_manager_id])
    team_lead = relationship("Dictionary", foreign_keys=[team_lead_id])
    project = relationship("Dictionary", foreign_keys=[project_id])
    city = relationship("Dictionary", foreign_keys=[city_id])
    source = relationship("Dictionary", foreign_keys=[source_id])
    internal_transfer = relationship("Dictionary", foreign_keys=[internal_transfer_id])
    replacement_type = relationship("Dictionary", foreign_keys=[replacement_type_id])
    employment_type = relationship("Dictionary", foreign_keys=[employment_type_id])
    feasibility = relationship("Dictionary", foreign_keys=[feasibility_id])
    block = relationship("Dictionary", foreign_keys=[block_id])
    weekly_reports = relationship("WeeklyReport", back_populates="vacancy", cascade="all, delete-orphan")
    delegations = relationship(
        "VacancyDelegation",
        foreign_keys="VacancyDelegation.vacancy_id",
        back_populates="vacancy",
        cascade="all, delete-orphan",
    )
    
    @property
    def work_duration_days(self):
                                                                                         
        start = self.open_date
        if not start:
            return None
        end = self.close_date or _date.today()
        wd = calculate_working_days(start, end)
        return max(0, wd - (self.hold_days or 0))

class WeeklyReport(Base):
                                                               
    __tablename__ = "weekly_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id", ondelete="CASCADE"), nullable=False)
    
                   
    report_date = Column(DateTime(timezone=True), server_default=func.now(), comment="Точная дата сохранения")
    week_start = Column(Date, nullable=True, comment="Дата понедельника этой недели")
    week_number = Column(Integer, nullable=False, comment="Номер недели (1-52)")
    year = Column(Integer, nullable=False)
    
                    
    resumes_sent = Column(Integer, default=0, comment="Передано заказчику")
    candidates_agreed = Column(Integer, default=0, comment="Резюме одобрено")
    interviews_planned = Column(Integer, default=0, comment="Собеседования план")
    interviews_conducted = Column(Integer, default=0, comment="Собеседования факт")
    offer_made = Column(Integer, default=0, comment="Оффер сделан")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
                   
    vacancy = relationship("Vacancy", back_populates="weekly_reports")

                                                                                     
                                                                            
                                                                              
class VacancyDelegation(Base):
\
\
\
       
    __tablename__ = "vacancy_delegations"

    id = Column(Integer, primary_key=True, index=True)
    vacancy_id = Column(
        Integer, ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    delegated_to_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    delegated_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    start_date = Column(Date, nullable=False, comment="Дата начала делегирования")
    end_date   = Column(Date, nullable=False, comment="Дата окончания делегирования")
    is_active  = Column(Boolean, default=True, nullable=False, comment="False = досрочно отозвано")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

                   
    vacancy      = relationship("Vacancy", foreign_keys=[vacancy_id], back_populates="delegations")
    delegated_to = relationship("User", foreign_keys=[delegated_to_id])
    delegated_by = relationship("User", foreign_keys=[delegated_by_id])

class VacancyHistory(Base):
                                     
    __tablename__ = "vacancy_history"

    id               = Column(Integer, primary_key=True, index=True)
    vacancy_id       = Column(Integer, ForeignKey("vacancies.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id",     ondelete="SET NULL"), nullable=True, index=True)
    action_type      = Column(String(20), nullable=False, index=True)
    changes          = Column(Text, nullable=True)
    vacancy_snapshot = Column(String(500), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    vacancy = relationship("Vacancy", foreign_keys=[vacancy_id])
    user    = relationship("User",    foreign_keys=[user_id])

from middleware.audit import AuditLog                                         
from services.refresh_token import RefreshToken                                        