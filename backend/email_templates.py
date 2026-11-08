"""
Модуль генерации минималистичных корпоративных HTML-шаблонов писем RMS.
Дизайн строго воспроизводит стиль эталонного шаблона Stripo (imported-from-stripo_The last day.html):
- Логотип RMS в шапке с фирменным фиолетовым градиентом системы (#4f46e5 -> #ec4899)
- Изображение: email_hero_banner.png
- Выравнивание текста, кнопки и подписи по левому краю
- Уменьшенные, естественные межстрочные отступы
- Темно-синий цвет кнопки действия (#0F2F64)
- Никаких смайликов и эмодзи
- Спокойная, сдержанная палитра: нейтральный фон #F6F6F6, белая подложка #FFFFFF, глубокий цвет текста #363C3B
- Динамическое определение базового URL системы (локальный тест или прод)
"""
import os
import html
from typing import List, Dict, Optional, Any


def get_default_base_url() -> str:
    return os.environ.get("RMS_BASE_URL", "http://rms-poc-sandbox.apps.stage.rt.ru").rstrip('/')


def render_rms_email_template(
    title: str,
    preheader: str = "",
    greeting: str = "Привет,",
    body_paragraphs: Optional[List[str]] = None,
    deadline_text: Optional[str] = None,
    cta_text: Optional[str] = "Перейти в систему RMS",
    cta_url: Optional[str] = None,
    info_items: Optional[List[Dict[str, Any]]] = None,
    sign_off_company: str = "RMS",
    hero_image_url: Optional[str] = None,
    footer_note: Optional[str] = None,
) -> str:
    """
    Генерирует минималистичный, спокойный HTML письма по эталону Stripo (выравнивание по левому краю).
    """
    system_url = (cta_url or get_default_base_url()).rstrip('/')
    banner_url = hero_image_url or f"{system_url}/email_hero_banner.png"
    safe_title = html.escape(title)
    safe_preheader = html.escape(preheader or title)

    # Paragraphs formatting (left-aligned with compact, natural spacing)
    paragraphs_html = ""
    if body_paragraphs:
        for idx, p in enumerate(body_paragraphs):
            # Less bottom margin between consecutive text lines
            b_margin = "8px" if idx < len(body_paragraphs) - 1 or deadline_text else "24px"
            paragraphs_html += f"""
              <p style="Margin: 0 0 {b_margin} 0; mso-line-height-rule: exactly; font-family: Outfit, Arial, -apple-system, sans-serif; line-height: 26px; letter-spacing: 0; font-weight: normal; color: #363C3B; font-size: 18px; text-align: left;">
                {p}
              </p>
            """

    # Deadline note without emojis, with bold text (compact spacing)
    deadline_html = ""
    if deadline_text:
        deadline_html = f"""
          <p style="Margin: 0 0 28px 0; mso-line-height-rule: exactly; font-family: Outfit, Arial, -apple-system, sans-serif; line-height: 26px; letter-spacing: 0; font-weight: normal; color: #363C3B; font-size: 18px; text-align: left;">
            {deadline_text}
          </p>
        """

    # CTA Button: Dark blue (#0F2F64), left-aligned, pill-shaped
    cta_html = ""
    if cta_text and cta_url:
        safe_cta_text = html.escape(cta_text)
        safe_cta_url = html.escape(cta_url)
        cta_html = f"""
          <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-spacing: 0px; margin: 20px 0 32px 0;">
            <tbody>
              <tr>
                <td align="left" style="padding: 0; Margin: 0; text-align: left;">
                  <!--[if mso]>
                  <a href="{safe_cta_url}" target="_blank" hidden>
                    <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{safe_cta_url}" style="height:46px; v-text-anchor:middle; width:220px" arcsize="50%" stroke="f" fillcolor="#0F2F64">
                      <w:anchorlock/>
                      <center style="color:#ffffff; font-family:Outfit, Arial; font-size:16px; font-weight:500; line-height:16px;">
                        {safe_cta_text}
                      </center>
                    </v:roundrect>
                  </a>
                  <![endif]-->
                  <!--[if !mso]><!-- -->
                  <span style="display: inline-block; background-color: #0F2F64; border-radius: 30px;">
                    <a href="{safe_cta_url}" target="_blank" style="mso-style-priority: 100 !important; text-decoration: none !important; color: #FFFFFF; font-size: 16px; font-weight: 500; padding: 13px 34px; display: inline-block; background-color: #0F2F64; border-radius: 30px; font-family: Outfit, Arial, -apple-system, sans-serif; line-height: 20px; text-align: center;">
                      {safe_cta_text}
                    </a>
                  </span>
                  <!--<![endif]-->
                </td>
              </tr>
            </tbody>
          </table>
        """

    # Info Items Box - minimal and left-aligned
    info_box_html = ""
    if info_items:
        items_rows = []
        for idx, item in enumerate(info_items):
            label = html.escape(item.get("label", ""))
            val = item.get("value", "")
            is_link = item.get("is_link", False)
            is_code = item.get("is_code", False)

            if is_link:
                val_content = f'<a href="{html.escape(val)}" target="_blank" style="color: #0F2F64; text-decoration: underline; font-weight: 500; word-break: break-all;">{html.escape(val)}</a>'
            elif is_code:
                val_content = f'<span style="display: inline-block; margin-top: 6px; font-family: Consolas, Monaco, monospace; font-size: 13px; color: #334155; word-break: break-all; background-color: #EEF2F6; padding: 4px 8px; border-radius: 4px;">{html.escape(val)}</span>'
            else:
                val_content = f'<span style="color: #1E293B; font-weight: 500;">{html.escape(val)}</span>'

            divider = '<div style="height: 1px; background-color: #E2E8F0; margin: 14px 0;"></div>' if idx > 0 else ''
            items_rows.append(f"""
              {divider}
              <div style="font-family: Outfit, Arial, sans-serif; font-size: 14px; color: #475569; line-height: 22px; text-align: left;">
                <strong style="font-weight: 700 !important; color: #1E293B;">{label}</strong><br>
                {val_content}
              </div>
            """)

        info_box_html = f"""
          <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-spacing: 0px; margin: 0 0 32px 0; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;">
            <tbody>
              <tr>
                <td style="padding: 20px 24px; text-align: left;">
                  {''.join(items_rows)}
                </td>
              </tr>
            </tbody>
          </table>
        """

    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html dir="ltr" xmlns="http://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office" lang="ru">
<head>
  <meta charset="UTF-8">
  <meta content="width=device-width, initial-scale=1" name="viewport">
  <meta name="x-apple-disable-message-reformatting">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta content="telephone=no" name="format-detection">
  <title>{safe_title}</title>
  <!--[if (mso 16)]>
  <style type="text/css">
    a {{ text-decoration: none; }}
  </style>
  <![endif]-->
  <!--[if gte mso 9]>
  <noscript>
    <xml>
      <o:OfficeDocumentSettings>
        <o:AllowPNG></o:AllowPNG>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
  </noscript>
  <![endif]-->
  <!--[if mso]>
  <xml>
    <w:WordDocument xmlns:w="urn:schemas-microsoft-com:office:word">
      <w:DontUseAdvancedTypographyReadingMail/>
    </w:WordDocument>
  </xml>
  <![endif]-->
  <!--[if !mso]><!-- -->
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap">
  <!--<![endif]-->
  <style type="text/css">
    u + .body img ~ div div {{ display: none; }}
    #outlook a {{ padding: 0; }}
    span.MsoHyperlink, span.MsoHyperlinkFollowed {{ color: inherit; mso-style-priority: 99; }}
    a.es-button {{ mso-style-priority: 100 !important; text-decoration: none !important; }}
    a[x-apple-data-detectors], #MessageViewBody a {{
      color: inherit !important;
      text-decoration: none !important;
      font-size: inherit !important;
      font-family: inherit !important;
      font-weight: inherit !important;
      line-height: inherit !important;
    }}
    @media only screen and (max-width: 600px) {{
      .es-content-body, .es-header-body, .es-footer-body {{
        width: 100% !important;
      }}
      .adapt-img {{
        width: 100% !important;
        height: auto !important;
      }}
      .content-padding {{
        padding: 30px 24px !important;
      }}
      h1 {{
        font-size: 28px !important;
        line-height: 36px !important;
      }}
      p {{
        font-size: 16px !important;
        line-height: 24px !important;
      }}
    }}
  </style>
</head>
<body class="body" style="width: 100%; height: 100%; font-family: Outfit, Arial, -apple-system, sans-serif; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; padding: 0; Margin: 0;">
  <!-- Preheader text -->
  <div style="display: none; font-size: 1px; color: #F6F6F6; line-height: 1px; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;">
    {safe_preheader}
  </div>

  <div dir="ltr" class="es-wrapper-color" style="background-color: #F6F6F6; padding: 24px 0 40px 0;">
    <!--[if gte mso 9]>
    <v:background xmlns:v="urn:schemas-microsoft-com:vml" fill="t">
      <v:fill type="tile" color="#f6f6f6"></v:fill>
    </v:background>
    <![endif]-->

    <table width="100%" cellspacing="0" cellpadding="0" class="es-wrapper" role="none" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-spacing: 0px; padding: 0; Margin: 0; width: 100%; height: 100%;">
      <tbody>
        <tr>
          <td valign="top" align="center" style="padding: 0; Margin: 0;">

            <!-- Header: Logo RMS with the system violet/purple gradient (#4f46e5 -> #ec4899) -->
            <table cellspacing="0" cellpadding="0" align="center" class="es-header" role="none" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-spacing: 0px; width: 100%; table-layout: fixed !important; background-color: transparent;">
              <tbody>
                <tr>
                  <td align="center" style="padding: 0; Margin: 0;">
                    <table cellspacing="0" cellpadding="0" bgcolor="#ffffff" align="center" class="es-header-body" role="none" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-spacing: 0px; background-color: #FFFFFF; width: 600px;">
                      <tbody>
                        <tr>
                          <td align="left" style="padding: 36px 40px 24px 40px; Margin: 0; text-align: left;">
                            <div style="font-family: Outfit, Arial, -apple-system, sans-serif; font-size: 32px; font-weight: 800; letter-spacing: -0.5px; line-height: 36px;">
                              <!-- System Violet Gradient -->
                              <span style="background: linear-gradient(135deg, #4f46e5 0%, #ec4899 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; color: #7c3aed; display: inline-block;">
                                RMS
                              </span>
                            </div>
                            <div style="font-family: Outfit, Arial, -apple-system, sans-serif; font-size: 12px; font-weight: 500; color: #8C8C8C; letter-spacing: 1px; text-transform: uppercase; margin-top: 4px;">
                              Recruitment Management System
                            </div>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </td>
                </tr>
              </tbody>
            </table>

            <!-- Content: Hero Image & Body -->
            <table cellspacing="0" cellpadding="0" align="center" class="es-content" role="none" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-spacing: 0px; width: 100%; table-layout: fixed !important;">
              <tbody>
                <tr>
                  <td align="center" style="padding: 0; Margin: 0;">
                    <table cellspacing="0" cellpadding="0" bgcolor="#ffffff" align="center" class="es-content-body" role="none" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-spacing: 0px; background-color: #FFFFFF; width: 600px;">
                      <tbody>

                        <!-- Hero Image (email_hero_banner.png) -->
                        <tr>
                          <td align="center" style="padding: 0; Margin: 0; font-size: 0;">
                            <img src="{banner_url}" alt="RMS" width="600" class="adapt-img" style="display: block; font-size: 20px; border: 0; outline: none; text-decoration: none; margin: 0; width: 100%; max-width: 600px; height: auto;" />
                          </td>
                        </tr>

                        <!-- Body Content Area (Left-aligned, Stripo style) -->
                        <tr>
                          <td class="content-padding" align="left" style="padding: 40px; Margin: 0; text-align: left;">

                            <!-- Title (Left-aligned) -->
                            <h1 style="Margin: 0 0 24px 0; font-family: Outfit, Arial, -apple-system, sans-serif; mso-line-height-rule: exactly; letter-spacing: 0; font-size: 34px; font-style: normal; font-weight: 600; line-height: 42px; color: #1E293B; text-align: left;">
                              {safe_title}
                            </h1>

                            <!-- Greeting with compact bottom margin -->
                            {f'<p style="Margin: 0 0 6px 0; mso-line-height-rule: exactly; font-family: Outfit, Arial, -apple-system, sans-serif; line-height: 26px; letter-spacing: 0; font-weight: normal; color: #363C3B; font-size: 18px; text-align: left;">{html.escape(greeting)}</p>' if greeting else ''}

                            <!-- Paragraphs (compact spacing) -->
                            {paragraphs_html}

                            <!-- Deadline / Important Note (compact spacing) -->
                            {deadline_html}

                            <!-- Action Button (Left-aligned, Dark Blue) -->
                            {cta_html}

                            <!-- Info Box (Left-aligned) -->
                            {info_box_html}

                            <!-- Sign-off (Left-aligned, Stripo style) -->
                            <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-spacing: 0px; margin-top: 32px;">
                              <tbody>
                                <tr>
                                  <td align="left" style="padding: 0; Margin: 0; text-align: left;">
                                    <p style="Margin: 0; mso-line-height-rule: exactly; font-family: Outfit, Arial, -apple-system, sans-serif; line-height: 26px; letter-spacing: 0; font-weight: normal; color: #363C3B; font-size: 17px; text-align: left;">
                                      С уважением,<br>
                                      Команда <strong style="font-weight: 700 !important; color: #1E293B;">{html.escape(sign_off_company)}</strong>.
                                    </p>
                                  </td>
                                </tr>
                              </tbody>
                            </table>

                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </td>
                </tr>
              </tbody>
            </table>

            <!-- Footer: Left-aligned -->
            <table cellspacing="0" cellpadding="0" align="center" class="es-footer" role="none" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-spacing: 0px; width: 100%; table-layout: fixed !important; background-color: transparent;">
              <tbody>
                <tr>
                  <td align="center" style="padding: 0; Margin: 0;">
                    <table cellspacing="0" cellpadding="0" bgcolor="#ffffff" align="center" class="es-footer-body" role="none" style="mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-spacing: 0px; background-color: transparent; width: 600px;">
                      <tbody>
                        <tr>
                          <td align="left" style="padding: 24px 40px 40px 40px; Margin: 0; text-align: left;">
                            <p style="Margin: 0 0 6px 0; mso-line-height-rule: exactly; font-family: Outfit, Arial, sans-serif; line-height: 20px; letter-spacing: 0; font-weight: 600; color: #64748B; font-size: 13px; text-align: left;">
                              RMS &bull; Recruitment Management System
                            </p>
                            <p style="Margin: 0; mso-line-height-rule: exactly; font-family: Outfit, Arial, sans-serif; line-height: 18px; letter-spacing: 0; font-weight: normal; color: #94A3B8; font-size: 12px; text-align: left;">
                              {html.escape(footer_note or "Это автоматическое сервисное уведомление. Пожалуйста, не отвечайте на данное письмо.")}
                            </p>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </td>
                </tr>
              </tbody>
            </table>

          </td>
        </tr>
      </tbody>
    </table>
  </div>
</body>
</html>
"""


def get_recruiter_weekly_reminder_html(base_url: Optional[str] = None) -> str:
    r"""
    Генерирует еженедельное письмо рекрутерам строго по утвержденным требованиям:
    "Привет, не забудь заполнить отчет по вакансиям за текущую неделю.
    Срок заполнения- сегодня до конца рабочего дня. 

    Система http://rms-poc-sandbox.apps.stage.rt.ru/
    Инструкция по работе в системе \\sks10fs003.ks.rt.ru\RTI\Общая\Прием\БАЗА_ЗНАНИЙ\Рекрутмент\RMS система"
    """
    url = (base_url or get_default_base_url()).rstrip('/')
    return render_rms_email_template(
        title="Заполнение отчетности в RMS",
        preheader="Напоминание о заполнении отчета по вакансиям за текущую неделю",
        greeting="Привет,",
        body_paragraphs=[
            "не забудь заполнить отчет по вакансиям за текущую неделю."
        ],
        deadline_text='Срок заполнения — <strong style="font-weight: 700 !important; color: #1E293B;">сегодня до конца рабочего дня</strong>.',
        cta_text="Перейти в систему RMS",
        cta_url=url,
        info_items=[
            {
                "label": "Система:",
                "value": f"{url}/",
                "is_link": True,
            },
            {
                "label": "Инструкция по работе в системе:",
                "value": r"\\sks10fs003.ks.rt.ru\RTI\Общая\Прием\БАЗА_ЗНАНИЙ\Рекрутмент\RMS система",
                "is_code": True,
            },
        ],
        sign_off_company="RMS",
        hero_image_url=f"{url}/email_hero_banner.png",
        footer_note="Вы получили это письмо, так как являетесь ответственным рекрутером в системе RMS."
    )


def get_registration_email_html(full_name: str, email: str, password: str, base_url: Optional[str] = None) -> str:
    """
    Генерирует официальное корпоративное письмо о регистрации нового пользователя в системе RMS
    строго в стиле эталонного Stripo-шаблона (без смайликов, выравнивание по левому краю,
    фирменный фиолетовый градиент логотипа, темная кнопка, баннер email_hero_banner.png).
    """
    url = (base_url or get_default_base_url()).rstrip('/')
    return render_rms_email_template(
        title="Регистрация в системе RMS",
        preheader="Ваши учетные данные для доступа в систему управления подбором персонала RMS",
        greeting=f"Здравствуйте, {full_name}!",
        body_paragraphs=[
            "Для вас создана учетная запись в системе управления подбором персонала RMS."
        ],
        deadline_text='При первом входе система потребует <strong style="font-weight: 700 !important; color: #1E293B;">сменить временный пароль</strong> на собственный постоянный.',
        cta_text="Войти в систему RMS",
        cta_url=url,
        info_items=[
            {"label": "Логин (Email):", "value": email},
            {"label": "Временный пароль:", "value": password, "is_code": True},
            {"label": "Адрес системы:", "value": f"{url}/", "is_link": True},
        ],
        sign_off_company="RMS",
        hero_image_url=f"{url}/email_hero_banner.png",
        footer_note="Вы получили это письмо, так как зарегистрированы в системе RMS."
    )


def get_welcome_email_html(full_name: str, email: str, password: str, base_url: Optional[str] = None) -> str:
    """
    Алиас для get_registration_email_html (обратная совместимость).
    """
    return get_registration_email_html(full_name=full_name, email=email, password=password, base_url=base_url)


def get_password_reset_email_html(full_name: str, email: str, password: str, base_url: Optional[str] = None) -> str:
    """
    Генерирует письмо со сбросом пароля.
    """
    url = (base_url or get_default_base_url()).rstrip('/')
    return render_rms_email_template(
        title="Сброс пароля в RMS",
        preheader="Ваш временный пароль для входа в RMS",
        greeting=f"Здравствуйте, {full_name}!",
        body_paragraphs=[
            "Ваш пароль был сброшен. Используйте новый временный пароль для входа."
        ],
        deadline_text='При входе система потребует <strong style="font-weight: 700 !important; color: #1E293B;">создать новый постоянный пароль</strong>.',
        cta_text="Войти в систему RMS",
        cta_url=url,
        info_items=[
            {"label": "Логин:", "value": email},
            {"label": "Новый пароль:", "value": password, "is_code": True},
            {"label": "Адрес системы:", "value": f"{url}/", "is_link": True},
        ],
        sign_off_company="RMS",
        hero_image_url=f"{url}/email_hero_banner.png",
    )
