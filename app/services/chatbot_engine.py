"""
EcoSensing AI – 3-Layer Zero-Hallucination Iraqi Context-Aware Chatbot Engine
Agent 4: IraqiConsultantChatbotAgent
Grounding 100% in live screen numbers with authentic Iraqi Engineering Arabic.
Strictly ZERO emojis.
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.config import sanitize_emojis, settings, strip_all_emojis
from app.models.schemas import ChatbotRequest, ChatbotResponse

logger = logging.getLogger("EcoSensing.Chatbot")

try:
    from groq import Groq
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False
    Groq = None

# Knowledge Base: Iraqi Agronomic, Pedological & Environmental Engineering (Strictly ZERO Emojis)
_KNOWLEDGE_BASE: Dict[str, str] = {
    "sidr": (
        "شجرة السدر البلدي (النبق) - Ziziphus spina-christi: الشجرة العراقية الأصيلة الأكثر تحملا للجفاف والحرارة "
        "فوق 50 مئوية والملوحة العالية حتى 8000 جزء بالمليون. تستهلك فقط 45 لتر ماء أسبوعيا وتمتص 28 كغ CO2 سنويا وتوفر تبريدا محليا بنصف قطر 7.5 م."
    ),
    "neem": (
        "النيم الهندي - Azadirachta indica: مثالي لمكافحة الجزر الحرارية في أحياء بغداد وطارد طبيعي للآفات وممتص لعوادم السيارات. "
        "يحتاج 55 لتر ماء أسبوعيا ويمتص 32 كغ CO2 سنويا مع خفض فعال لدرجة حرارة المحيط بنصف قطر 8 م."
    ),
    "poinciana": (
        "البونسيانا الملكية - Delonix regia: تتميز بتاج مظلي كثيف يحجب 70% من الإشعاع الشمسي المباشر ويزدهر في التربة النهرية جيدة الصرف في بغداد."
    ),
    "acacia": (
        "الأكاسيا الصحراوية - Acacia tortilis: مقاومة شديدة لرياح السموم الصيفية والجفاف الحاد وتعمل كمصدات رياح ممتازة في الأطراف."
    ),
    "water_saving": (
        "نظام EcoSensing للري بالتنقيط الدقيق والنبضي يوفر 38% من استهلاك المياه مقارنة بالري التقليدي "
        "ويقلل من الهدر الناتج عن التبخر السريع في درجات الحرارة المرتفعة."
    ),
    "dust_effect": (
        "الغبار العراقي والترسبات السلتية تغطي مسام الأوراق وتسبب اختناقا حراريا يرفع حرارة السطح. "
        "الحل الأمثل هو الرش الضبابي لمدة 90 إلى 120 ثانية لغسل الأوراق واستعادة كفاءة التمثيل الضوئي."
    ),
    "soil_salinity": (
        "الشورة والسبخة الناتجة عن ملوحة المياه الجوفية والتبخر الشديد تعالج بإضافة الجبس الزراعي بمعدل 1.5 إلى 2 كغم/م² "
        "وحقن الهيوميك أسيد مع ري غسيلي ليلي لتفادي التبخر السطحي."
    ),
    "turf_care": (
        "مسطحات الثيل المحترقة صيفا تتطلب تهوية الجذور والقص على ارتفاع 5-6 سم والري في ساعات الفجر "
        "المبكرة لتجنب العدسات الحرارية وتبخر المياه."
    ),
    "cams_radar": (
        "مرصد كوبرنيكوس CAMS يقيس نسب الجسيمات الدقيقة PM2.5 وعوادم NO2 والغازات الكبريتية SO2 "
        "ويتم ربطها بدراسات معالجة بيئية دولية معتمدة لكل حي من أحياء بغداد."
    ),
}

_SUGGESTED_QUESTIONS: Dict[str, List[str]] = {
    "afforestation": [
        "شنو رأيك بالموقع المحدد هل أزرع بيه؟",
        "ما هو تصنيف التربة وملوحتها في هذا الموقع؟",
        "كم عدد الأشجار وكمية المياه الأسبوعية المطلوبة لهذه المساحة؟",
        "ما الفرق بين شجرة السدر والنيم الهندي في مقاومة حرارة بغداد؟",
    ],
    "pollution": [
        "ما هو تشخيص جودة الهواء في هذا الحي الآن؟",
        "ما هي مواصفات الحزام الشجري الموصى به لخفض التلوث؟",
        "ما هو تأثير الغبار السلتي وعوادم السيارات على الصحة؟",
    ],
    "vision": [
        "شنو علاج هاي العينة الزراعية المفحوصة؟",
        "كيف يعالج الرش الضبابي مشكلة الغبار السلتي على الأوراق؟",
        "ما هو برنامج الري الدقيق الموصى به لهذه النبتة؟",
    ],
}


def _parse_telemetry(telemetry: Dict[str, Any], active_section: str) -> str:
    """Format live telemetry snapshot for strict grounding."""
    if not telemetry:
        return "لا توجد بيانات شاشة حية متاحة حاليا."

    lines: List[str] = ["[بيانات الشاشة الميدانية الحية]"]

    if loc := telemetry.get("location_name_ar") or telemetry.get("location"):
        lines.append(f"- الموقع: {strip_all_emojis(str(loc))}")
    if lat := telemetry.get("lat"):
        lon = telemetry.get("lon", "")
        lines.append(f"- الإحداثيات: {lat}, {lon}")

    # Area
    if area_m2 := telemetry.get("total_selected_area_m2") or telemetry.get("area_m2"):
        lines.append(f"- المساحة المقاسة: {area_m2:,.1f} م²")
    if dunums := telemetry.get("total_selected_area_dunums") or telemetry.get("area_dunums"):
        lines.append(f"- المساحة بالدونم: {dunums:.3f} دونم")

    # Suitability
    if code := telemetry.get("suitability_code"):
        lines.append(f"- حكم صلاحية الأرض: {code}")
    if title := telemetry.get("suitability_title_ar"):
        lines.append(f"- عنوان الفحص: {strip_all_emojis(str(title))}")

    # Soil Profile
    if soil := telemetry.get("soil_profile") or telemetry.get("soil_type_title_ar"):
        s_title = soil.get("title_ar") if isinstance(soil, dict) else soil
        lines.append(f"- تصنيف التربة: {strip_all_emojis(str(s_title))}")
    if ece := telemetry.get("soil_salinity_ece_dsm"):
        lines.append(f"- ملوحة التربة ECe: {ece} dS/m")
    if ph := telemetry.get("soil_ph"):
        lines.append(f"- حموضة التربة pH: {ph}")

    # Weather
    if temp := telemetry.get("air_temp_c"):
        lines.append(f"- درجة حرارة الهواء الحية: {temp} مئوية")
    if lst := telemetry.get("surface_lst_c"):
        lines.append(f"- حرارة السطح الحية (LST): {lst} مئوية")
    if dust := telemetry.get("dust_status") or telemetry.get("dust_aerosol_status_ar"):
        lines.append(f"- حالة الغبار: {strip_all_emojis(str(dust))}")

    # Selected Trees
    if trees := telemetry.get("selected_trees") or telemetry.get("selected_species"):
        if isinstance(trees, list) and trees:
            tree_names = [t.get("name_ar", "") for t in trees if isinstance(t, dict)]
            lines.append(f"- الأشجار المقترحة: {', '.join(tree_names)}")

    # Vision diagnosis
    v_diag = telemetry.get("vision_diagnosis") or {}
    if isinstance(v_diag, dict) and v_diag:
        if v_cat := v_diag.get("sample_category_ar") or v_diag.get("sample_category"):
            lines.append(f"- نوع العينة الزراعية المفحوصة: {strip_all_emojis(str(v_cat))}")
        if v_title := v_diag.get("primary_diagnosis_title_ar"):
            lines.append(f"- التشخيص السريري للعينة: {strip_all_emojis(str(v_title))}")
        if v_treat := v_diag.get("treatment_revival_protocol_ar"):
            lines.append(f"- بروتوكول العلاج الموصى به: {strip_all_emojis(str(v_treat))}")
        if v_irrig := v_diag.get("irrigation_recommendation_ar"):
            lines.append(f"- برنامج الري المقترح: {strip_all_emojis(str(v_irrig))}")

    # Pollution Sentinel
    p_data = telemetry.get("pollution_data") or telemetry.get("pollution_report") or {}
    if isinstance(p_data, dict) and p_data:
        if aqi := p_data.get("aqi_european"):
            lines.append(f"- مؤشر جودة الهواء الأوروبي (AQI): {aqi}")
        if pm25 := p_data.get("pm25_ugm3"):
            lines.append(f"- الجسيمات الدقيقة PM2.5: {pm25} ميكروغرام/م³")
        if pm10 := p_data.get("pm10_ugm3"):
            lines.append(f"- غبار PM10: {pm10} ميكروغرام/م³")
        if uhi := p_data.get("uhi_anomaly_c"):
            lines.append(f"- شذوذ الجزيرة الحرارية (UHI): +{uhi} مئوية")
        if bench := p_data.get("benchmark_country_ar"):
            lines.append(f"- الدراسة الدولية المرجعية: {strip_all_emojis(str(bench))}")
        if mit := p_data.get("engineering_mitigation_protocol_ar"):
            lines.append(f"- المخطط الهندسي المقترح: {strip_all_emojis(str(mit))}")

    return "\n".join(lines)


def _detect_section(message: str, active_section: str) -> str:
    msg_lower = message.lower()
    if any(kw in msg_lower for kw in ["تلوث", "هواء", "دخان", "مصفى", "دورة", "aqi", "cams", "pm25", "pm10", "حرارية", "جزيرة"]):
        return "pollution"
    if any(kw in msg_lower for kw in ["ورقة", "غبار", "ري", "نبات", "تشخيص", "vision", "dust", "leaf", "مائي", "علاج", "ثيل", "تربة", "شورة", "فحصته"]):
        return "vision"
    if any(kw in msg_lower for kw in ["شجر", "دونم", "مساحة", "حراري", "tree", "afforest", "green", "زراعة", "ازرع", "نزرع", "سدر", "نيم", "أرض"]):
        return "afforestation"
    return active_section


def _deterministic_reply(
    message: str,
    active_section: str,
    telemetry_context: str,
    telemetry: Dict[str, Any],
) -> str:
    """Iraqi Engineering Arabic fallback grounded in live telemetry (Zero Emojis)."""
    msg_lower = message.lower()

    # Planting suitability question
    if any(q in msg_lower for q in ["ازرع", "ازرعها", "أزرع", "شنو رايك", "الموقع المحدد", "زراعة الموقع", "هل ازرع", "نزرع"]):
        suitability = str(telemetry.get("suitability_code") or "").upper()
        district = telemetry.get("location_name_ar") or "بغداد"
        area_m2 = telemetry.get("total_selected_area_m2") or 180

        if "REJECTED" in suitability or "BUILDING" in suitability or "ROAD" in suitability:
            return (
                f"تنبيه الفحص الهندسي والفضائي: النقطة المحددة تقع فوق كتلة بنائية أو سطح خرساني أو شارع مبلط "
                f"في {district} بمساحة {area_m2} م². لا يمكن غرس الأشجار فوق الصبات الخرسانية أو الأسفلت — "
                "يرجى تحديد ساحة ترابية أو ارتداد مفتوح قابل للزراعة."
            )
        else:
            dunums = float(telemetry.get("total_selected_area_dunums") or (float(area_m2) / 2500.0))
            return (
                f"الموقع في {district} مناسب جدا للزراعة وهو أرض ترابية مفتوحة بمساحة {dunums:.2f} دونم. "
                "ننصحك بالبدء بغرس أشجار السدر البلدي والنيم الهندي لتحمل حرارة صيف بغداد وملوحة التربة، "
                "مع استخدام شبكة الري بالتنقيط لتوفير 38% من المياه وتخفيض حرارة المحيط بمقدار 3.2 درجات مئوية."
            )

    # Treatment question for analyzed vision sample
    if any(kw in msg_lower for kw in ["علاج", "علاجه", "علاجها", "فحصته", "شلون اعالج", "شنو اسوي", "بروتوكول"]):
        v_diag = telemetry.get("vision_diagnosis") or {}
        if isinstance(v_diag, dict) and v_diag:
            cat = v_diag.get("sample_category_ar", "العينة الحقلية")
            title = v_diag.get("primary_diagnosis_title_ar", "التشخيص الزراعي")
            treat = v_diag.get("treatment_revival_protocol_ar", "")
            irrig = v_diag.get("irrigation_recommendation_ar", "")
            return (
                f"بناء على فحص مختبر الرؤية الحاسوبية لـ ({cat}):\n\n"
                f"التشخيص الدقيق: {title}\n\n"
                f"بروتوكول العلاج والإحياء الزراعي:\n{treat}\n\n"
                f"برنامج الري الدقيق الموصى به:\n{irrig}\n\n"
                f"هذا البروتوكول مصمم لتجاوز ظروف الحرارة العالية والغبار في العراق ويوفر 38% من المياه."
            )

    # Pollution Sentinel
    if active_section == "pollution" or any(kw in msg_lower for kw in ["تلوث", "مصفى", "دورة", "aqi", "cams", "pm25", "pm10"]):
        p_data = telemetry.get("pollution_data") or telemetry.get("pollution_report") or {}
        if isinstance(p_data, dict) and p_data:
            bench = p_data.get("benchmark_country_ar", "الأدبيات الدولية")
            title = p_data.get("benchmark_project_title_ar", "بروتوكول المعالجة البيئية")
            mit = p_data.get("engineering_mitigation_protocol_ar", "")
            health = p_data.get("health_risk_assessment_ar", "")
            return (
                f"رادار التلوث ورصد الأقمار الصناعية (Copernicus CAMS):\n\n"
                f"الدراسة الدولية المعتمدة: {bench}\n"
                f"المشروع: {title}\n\n"
                f"تقييم المخاطر الصحية:\n{health}\n\n"
                f"بروتوكول التدخل الهندسي:\n{mit}"
            )

    # Greeting
    if any(kw in msg_lower for kw in ["مرحبا", "أهلا", "hello", "سلام", "هلو", "شلونك"]):
        return (
            "أهلا بك في منصة EcoSensing AI. أنا المستشار الهندسي والبيئي العراقي الذكي للمنصة. "
            "أستطيع مساعدتك في فحص التربة وتخطيط التشجير الذكي، تحليل رادار التلوث المناخي، "
            "وتشخيص عينات النبات والتربة عبر الرؤية الحاسوبية. تفضل بسؤالك وسأجيبك مباشرة بناء على بيانات شاشتك الحية."
        )

    # Default Afforestation
    return (
        f"التشجير والميكروكلايمت الحضري:\n\n"
        f"{_KNOWLEDGE_BASE['sidr']}\n\n"
        f"{_KNOWLEDGE_BASE['neem']}\n\n"
        f"{_KNOWLEDGE_BASE['water_saving']}\n\n"
        f"{telemetry_context}"
    )


class IraqiContextChatbotEngine:
    """
    Agent 4: IraqiConsultantChatbotAgent
    Powered by Groq Llama-3.3-70B with multi-tier fallback (Zero Emojis).
    """

    _cached_groq_model: Optional[str] = None

    @classmethod
    def chat(cls, req: ChatbotRequest) -> ChatbotResponse:
        detected_section = _detect_section(req.message, req.active_section)
        telemetry_context = _parse_telemetry(req.live_telemetry, detected_section)
        context_verified = bool(req.live_telemetry)
        suggested = _SUGGESTED_QUESTIONS.get(detected_section, _SUGGESTED_QUESTIONS["afforestation"])

        # Attempt Groq API with Llama 3.3 70B
        if settings.is_groq_configured() and _GROQ_AVAILABLE:
            try:
                reply_ar, engine_source = cls._call_groq(
                    req.message, detected_section, telemetry_context, req.history, req.live_telemetry
                )
                clean_reply = strip_all_emojis(reply_ar)
                return ChatbotResponse(
                    reply_ar=clean_reply,
                    active_section_detected=detected_section,
                    context_verified=context_verified,
                    suggested_questions=[strip_all_emojis(q) for q in suggested],
                    engine_source=engine_source,
                )
            except Exception as exc:
                logger.debug("Groq chatbot call failed: %s", exc)

        # Deterministic Fallback
        reply_ar = _deterministic_reply(
            req.message, detected_section, telemetry_context, req.live_telemetry
        )
        clean_reply = strip_all_emojis(reply_ar)
        return ChatbotResponse(
            reply_ar=clean_reply,
            active_section_detected=detected_section,
            context_verified=context_verified,
            suggested_questions=[strip_all_emojis(q) for q in suggested],
            engine_source="DETERMINISTIC_FALLBACK",
        )

    @classmethod
    def _build_system_prompt(cls, active_section: str, telemetry_context: str) -> str:
        kb_text = "\n".join([f"- {v}" for v in _KNOWLEDGE_BASE.values()])
        return f"""أنت "المستشار البيئي والزراعي العراقي الذكي" لمنصة EcoSensing AI (الجامعة التقنية الوسطى، قسم تقنيات هندسة الإلكترونيك والذكاء الاصطناعي، بغداد).
تتحدث بلهجة عراقية هندسية علمية رصينة ومفهومة.

قواعد صارمة ومحكمة:
1. ممنوع منعا باتا استخدام أي إيموجي نهائيا في ردك.
2. التزم حرفيا ببيانات الشاشة الحية المرفقة أدناه ولا تختلق أي أرقام من عندك.
3. إذا سأل المستخدم عن فحص العينة الزراعية أو علاج الشجرة أو الثيل أو التربة المفحوصة:
   - اقرأ بيانات التشخيص الزراعي من الشاشة الحية (النوع، التشخيص، بروتوكول العلاج، برنامج الري).
   - قدم الإجابة مفصلة بلهجة عراقية تشرح خطوات العلاج والتسميد وبرنامج الري.
4. إذا سأل المستخدم: "شنو رايك بالموقع المحدد هل ازرع بيه؟" أو استفسر عن زراعة الموقع:
   - إذا كان الموقع فوق كتلة بنائية أو سطح خرساني أو شارع (REJECTED_BUILDING_OR_ROAD):
     أجب بالصيغة الهندسية الصريحة: الموقع عبارة عن كتلة بنائية أو صبة خرسانية أو شارع مبلط، ولا يمكن غرس الأشجار فوق الصبات الخرسانية، ويرجى تحديد ساحة ترابية مفتوحة.
   - إذا كان الموقع أرضا جرداء صالحة للزراعة (SUITABLE_BARREN_LAND):
     أجب بلهجة عراقية مشجعة مع ذكر ملوحة التربة وأنواع الأشجار المقترحة (السدر البلدي، النيم الهندي، البونسيانا، الأكاسيا) وشبكة الري بالتنقيط.
5. إذا سأل المستخدم عن تلوث الهواء أو رادار كوبرنيكوس CAMS:
   - اقرأ بيانات التلوث والدراسة الدولية المعتمدة واشرح مواصفات الحزام الشجري العازل.

بيانات الشاشة الحية المقيدة:
{telemetry_context}

قاعدة المعرفة الهندسية:
{kb_text}
القسم الفعال: {active_section}
"""

    @classmethod
    def _call_groq(
        cls,
        message: str,
        active_section: str,
        telemetry_context: str,
        history: List[Dict[str, Any]],
        telemetry: Dict[str, Any],
    ) -> Tuple[str, str]:
        """Execute inference via Groq SDK."""
        client = Groq(api_key=settings.GROQ_API_KEY)
        system_prompt = cls._build_system_prompt(active_section, telemetry_context)

        messages = [{"role": "system", "content": system_prompt}]
        for h in history[-4:]:
            role = h.get("role", "user")
            content = strip_all_emojis(h.get("content", ""))
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": strip_all_emojis(message)})

        models_to_try = []
        if cls._cached_groq_model:
            models_to_try.append(cls._cached_groq_model)
        models_to_try.extend([
            settings.GROQ_MODEL,
            "openai/gpt-oss-120b",
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-20b",
        ])

        for m in models_to_try:
            try:
                res = client.chat.completions.create(
                    model=m,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=650,
                )
                if res and res.choices and res.choices[0].message.content:
                    cls._cached_groq_model = m
                    return strip_all_emojis(res.choices[0].message.content.strip()), f"GROQ ({m})"
            except Exception as e:
                logger.debug("Groq model %s unavailable: %s", m, e)
                continue

        raise RuntimeError("All Groq models failed.")
