\
\
\
   
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from models import UserRole, DictionaryType

                                        
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TwoFactorVerifyRequest(BaseModel):
                                                    
    temp_token: str                                                   
    code: str                                           

class TwoFactorSetupResponse(BaseModel):
                                               
    secret: str                                                                                        
    qr_svg: str                                     
    uri: str                                              
    setup_id: str = ""                                                                     

class TwoFactorConfirmRequest(BaseModel):
                                                                                               
    code: str

class TwoFactorDisableRequest(BaseModel):
                                                                    
    code: str

                                        
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.RECRUITER

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.RECRUITER

class UserCreateWithPassword(BaseModel):
                                                    
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.RECRUITER
    password: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class ChangePasswordRequest(BaseModel):
    new_password: str
    confirm_password: str

class CompleteTourRequest(BaseModel):
                                               
    tour: str                           

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ChangeOwnPasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    is_temporary_password: Optional[bool] = None
    is_2fa_enabled: Optional[bool] = None
    is_vacancies_tour_completed: Optional[bool] = None
    is_reports_tour_completed: Optional[bool] = None
    created_at: Optional[datetime] = None

class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int

                                              
class DictionaryBase(BaseModel):
    type: DictionaryType
    value: str
    description: Optional[str] = None
    sort_order: int = 0

class DictionaryCreate(DictionaryBase):
    pass

class DictionaryUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class DictionaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    type: DictionaryType
    value: str
    description: Optional[str] = None
    sort_order: int
    is_active: bool

class DictionaryListResponse(BaseModel):
    items: List[DictionaryResponse]
    total: int

                                           
class VacancyBase(BaseModel):
    vacancy_id: Optional[str] = None
    open_date: Optional[date] = None
    quantity: int = 1
    level_id: Optional[int] = None
    position_name: str
    status_id: Optional[int] = None
    it_role_id: Optional[int] = None
    admin_manager_id: Optional[int] = None
    team_lead_id: Optional[int] = None
    project_id: Optional[int] = None
                                                
    resume_at_customer: int = 0
    resume_approved: int = 0
    interviews_fact: int = 0
    interviews_plan: int = 0
    offer_made: int = 0
    city_id: Optional[int] = None
    city_text: Optional[str] = None
    source_id: Optional[int] = None
    internal_transfer_id: Optional[int] = None
    status_changed_at: Optional[date] = None
    close_date: Optional[date] = None
    candidate_name: Optional[str] = None
    candidate_company: Optional[str] = None
    replacement_type_id: Optional[int] = None
    ex_employee_name: Optional[str] = None
    unit_id: Optional[str] = None
    employment_type_id: Optional[int] = None
    feasibility_id: Optional[int] = None
    iqhr_link: Optional[str] = None
    recruiter_id: Optional[int] = None
    block_id: Optional[int] = None
    hold_days: int = 0
    salary_gross: Optional[int] = None                          

class VacancyCreate(VacancyBase):
    pass

class VacancyUpdate(BaseModel):
    vacancy_id: Optional[str] = None
    open_date: Optional[date] = None
    quantity: Optional[int] = None
    level_id: Optional[int] = None
    position_name: Optional[str] = None
    status_id: Optional[int] = None
    it_role_id: Optional[int] = None
    admin_manager_id: Optional[int] = None
    team_lead_id: Optional[int] = None
    project_id: Optional[int] = None
    resume_at_customer: Optional[int] = None
    resume_approved: Optional[int] = None
    interviews_fact: Optional[int] = None
    interviews_plan: Optional[int] = None
    offer_made: Optional[int] = None
    city_id: Optional[int] = None
    city_text: Optional[str] = None
    source_id: Optional[int] = None
    internal_transfer_id: Optional[int] = None
    status_changed_at: Optional[date] = None
    close_date: Optional[date] = None
    candidate_name: Optional[str] = None
    candidate_company: Optional[str] = None
    replacement_type_id: Optional[int] = None
    ex_employee_name: Optional[str] = None
    unit_id: Optional[str] = None
    employment_type_id: Optional[int] = None
    feasibility_id: Optional[int] = None
    iqhr_link: Optional[str] = None
    recruiter_id: Optional[int] = None
    block_id: Optional[int] = None
    hold_days: Optional[int] = None
    salary_gross: Optional[int] = None                          

class ActiveDelegationInfo(BaseModel):
                                                        
    model_config = ConfigDict(from_attributes=True)
    id: int
    delegated_to_id: int
    start_date: date
    end_date: date
    is_active: bool
    delegated_to: Optional[UserResponse] = None

class VacancyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    vacancy_id: Optional[str] = None
    open_date: Optional[date] = None
    quantity: int
    level_id: Optional[int] = None
    position_name: str
    status_id: Optional[int] = None
    it_role_id: Optional[int] = None
    admin_manager_id: Optional[int] = None
    team_lead_id: Optional[int] = None
    project_id: Optional[int] = None
    resume_at_customer: int = 0
    resume_approved: int = 0
    interviews_fact: int = 0
    interviews_plan: int = 0
    offer_made: int = 0
    city_id: Optional[int] = None
    city_text: Optional[str] = None
    source_id: Optional[int] = None
    internal_transfer_id: Optional[int] = None
    status_changed_at: Optional[date] = None
    close_date: Optional[date] = None
    candidate_name: Optional[str] = None
    candidate_company: Optional[str] = None
    replacement_type_id: Optional[int] = None
    ex_employee_name: Optional[str] = None
    unit_id: Optional[str] = None
    employment_type_id: Optional[int] = None
    feasibility_id: Optional[int] = None
    iqhr_link: Optional[str] = None
    recruiter_id: Optional[int] = None
    block_id: Optional[int] = None
    hold_days: int = 0
    salary_gross: Optional[int] = None                          
                                                             
    resumes_sent_cnt: int = 0
    candidates_agreed_cnt: int = 0
    interviews_planned_cnt: int = 0
    interviews_conducted_cnt: int = 0
    created_at: Optional[datetime] = None
    
                     
    recruiter: Optional[UserResponse] = None
    level: Optional[DictionaryResponse] = None
    status: Optional[DictionaryResponse] = None
    it_role: Optional[DictionaryResponse] = None
    admin_manager: Optional[DictionaryResponse] = None
    team_lead: Optional[DictionaryResponse] = None
    project: Optional[DictionaryResponse] = None
    city: Optional[DictionaryResponse] = None
    source: Optional[DictionaryResponse] = None
    internal_transfer: Optional[DictionaryResponse] = None
    replacement_type: Optional[DictionaryResponse] = None
    employment_type: Optional[DictionaryResponse] = None
    feasibility: Optional[DictionaryResponse] = None
    block: Optional[DictionaryResponse] = None
    
                      
    work_duration_days: Optional[int] = None
    delegation: Optional[ActiveDelegationInfo] = None

class VacancyListResponse(BaseModel):
    items: List[VacancyResponse]
    total: int

                                                 
class WeeklyReportBase(BaseModel):
    week_number: int
    year: int
    resumes_sent: int = 0
    candidates_agreed: int = 0
    interviews_planned: int = 0
    interviews_conducted: int = 0
    offer_made: int = 0

class WeeklyReportCreate(WeeklyReportBase):
    vacancy_id: int

class WeeklyReportUpdate(BaseModel):
    resumes_sent: Optional[int] = None
    candidates_agreed: Optional[int] = None
    interviews_planned: Optional[int] = None
    interviews_conducted: Optional[int] = None
    offer_made: Optional[int] = None

class WeeklyReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    vacancy_id: int
    week_number: int
    year: int
    report_date: Optional[datetime] = None
    week_start: Optional[date] = None
    resumes_sent: int
    candidates_agreed: int
    interviews_planned: int
    interviews_conducted: int
    offer_made: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class WeeklyReportListResponse(BaseModel):
    items: List[WeeklyReportResponse]
    total: int

                                         
class ExportRequest(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    period: Optional[str] = None

                                                              
class TableFilter(BaseModel):
                                                 
    field: str
    value: Optional[List] = None

class TableSort(BaseModel):
                                          
    field: str
    order: str = "desc"

class SmartExportRequest(BaseModel):
                                                       
    period: Optional[str] = "all_time"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    apply_filters: bool = False
    filters: Optional[dict] = None
    sort_field: Optional[str] = None
    sort_order: Optional[str] = "desc"
    search: Optional[str] = None