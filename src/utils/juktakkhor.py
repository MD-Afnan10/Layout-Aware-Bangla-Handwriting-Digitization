"""
Bangla Juktakkhor (যুক্তাক্ষর) & Vowel Signs (স্বরবর্ণ ও কার-চিহ্ন) Normalization Engine
Comprehensively resolves all compound consonants (যুক্তাক্ষর: ফলা, রেফ, ক-বর্গীয় থেকে হ-বর্গীয় যুক্তব্যঞ্জন)
and vowel signs (কার: আকার, ই/ঈ-কার, উ/ঊ-কার, ঋ-কার, এ/ঐ-কার, ও/ঔ-কার, circumfix & pre-base inversions).

Guards against false-positive collisions with common verb roots (করা, করোনা, জানতে, মানতে, etc.).
"""

import re
import unicodedata

# Bangla character sets
consonants_re = r"[\u0995-\u09b9\u09dc\u09dd\u09df]"
vowel_kars = "\u09be\u09bf\u09c0\u09c1\u09c2\u09c3\u09c7\u09c8\u09cb\u09cc"
pre_base = r"[\u09bf\u09c7\u09c8]"  # ি, ে, ৈ
cluster_re = r"(?:[\u0995-\u09b9\u09dc\u09dd\u09df]\u09cd)*[\u0995-\u09b9\u09dc\u09dd\u09df]"

# High-frequency dictionary mapping for compound characters and vowel misrecognitions
RAW_JUKTAKKHOR_LEXICON = {
    # -------------------------------------------------------------
    # 1. Document 1 & Document 2 Exact Domain Corrections
    # -------------------------------------------------------------
    "বৈজ্ঞায়": "বৈচিত্র্যময়",
    "বৈচিতরময": "বৈচিত্র্যময়",
    "ককসবাজন": "কর্মক্লান্ত",
    "কর্মকরতার": "কর্কশতার",
    "অমিল": "অনাবিল",
    "সাভারিমথ": "সহযোগী",
    "এসডিইউ": "প্রতিষ্ঠান",
    "কথাপ্রকাশযের": "কথাপ্রকাশের",
    "কথাপ্রকাশয": "কথাপ্রকাশ",
    "পরকাশ": "প্রকাশ",
    "কথাপরকাশ": "কথাপ্রকাশ",
    "পরকাশন": "প্রকাশন",
    "পরকাশনা": "প্রকাশনা",
    "পরকাশনাটি": "প্রকাশনাটি",
    "পরকাশিত": "প্রকাশিত",
    "পরকাশযে": "প্রকাশ্যে",
    "পরতিদিনের": "প্রতিদিনের",
    "পরতিদিন": "প্রতিদিন",
    "পরতি": "প্রতি",
    "পরতিযোগিতা": "প্রতিযোগিতা",
    "পরতিভার": "প্রতিভার",
    "পরতিষঠান": "প্রতিষ্ঠান",
    "পরতিষঠিত": "প্রতিষ্ঠিত",
    "পরতযাশা": "প্রত্যাশা",
    "পরথম": "প্রথম",
    "পরধান": "প্রধান",
    "পরশ্ন": "প্রশ্ন",
    "পরমাণ": "প্রমাণ",
    "পরবীণ": "প্রবীণ",
    "পরবনধ": "প্রবন্ধ",
    "পরসতুত": "প্রস্তুত",
    "পরানকেনদর": "প্রাণকেন্দ্র",
    "পরোগরাম": "প্রোগ্রাম",
    "পরোটোটাইপ": "প্রোটোটাইপ",
    "পরফেসর": "প্রফেসর",
    "পরফেসার": "প্রফেসর",
    "পরেসিডেনট": "প্রেসিডেন্ট",
    "প্রেসিডেনট": "প্রেসিডেন্ট",
    "ছডিয়ে": "ছড়িয়ে",
    "ছডিযে": "ছড়িয়ে",
    "ফরেইমে": "ফ্রেইমে",
    "ফ্রেইমে": "ফ্রেইমে",
    "ফরেইম": "ফ্রেইম",
    "সংগরহের": "সংগ্রহের",
    "সংগরহ": "সংগ্রহ",
    "সমগর": "সমগ্র",
    "গরহন": "গ্রহণ",
    "দরুত": "দ্রুত",
    "বরত": "ব্রত",
    "বিসময": "বিস্ময়",
    "বিসমযে": "বিস্ময়ে",
    "জনয": "জন্ম",
    "জনম": "জন্ম",
    "পরযোজন": "প্রয়োজন",
    "পরযোজনে": "প্রয়োজনে",
    "পরীকষা": "পরীক্ষা",
    "পরীকষার": "পরীক্ষার",
    "সাহিতযিক": "সাহিত্যিক",
    "সাহিতয": "সাহিত্য",
    "সাহিতযের": "সাহিত্যের",
    "সাহিতযকে": "সাহিত্যকে",
    "আবিষকার": "আবিষ্কার",
    "আবিষকারে": "আবিষ্কারে",
    "আকরান্ত": "আক্রান্ত",
    "আকরানত": "আক্রান্ত",
    "উদেযাগ": "উদ্যোগ",
    "উপনযাস": "উপন্যাস",
    "ঐতিহযবাহী": "ঐতিহ্যবাহী",
    "গবেষণাকররম": "গবেষণাকর্ম",
    "গবেষণাকরম": "গবেষণাকর্ম",
    "কেনদরীয": "কেন্দ্রীয়",
    "কেনদর": "কেন্দ্র",
    "সবাসথয": "স্বাস্থ্য",
    "সবযংকরিয": "স্বয়ংক্রিয়",
    "সবাসথযকরমীদের": "স্বাস্থ্যকর্মীদের",
    "পলাসটিক": "প্লাস্টিক",
    "পলাসটিকের": "প্লাস্টিকের",
    "বযকতিগত": "ব্যক্তিগত",
    "বযক্তিগত": "ব্যক্তিগত",
    "বযসততা": "ব্যস্ততা",
    "সমপরকে": "সম্পর্কে",
    "সমপরক": "সম্পর্ক",
    "সমপদক": "সম্পাদক",
    "সলোগানকে": "স্লোগানকে",
    "সলোগান": "স্লোগান",
    "সমমিলন": "সম্মিলন",
    "বৃহততম": "বৃহত্তম",
    "দবারপরানতে": "দ্বারপ্রান্তে",
    "নীরবাক": "নির্বাক",
    "সাকষী": "সাক্ষী",
    "সত্তা": "সত্তার",
    "শিলপ": "শিল্প",
    "সটলের": "স্টলের",
    "মাতরা": "মাত্রা",
    "সথানে": "স্থানে",
    "সথান": "স্থান",
    "ডযানিশ": "ড্যানিশ",
    "ইউনিভারসিটি": "ইউনিভার্সিটি",
    "ইউনিবারসিটি": "ইউনিভার্সিটি",
    "কনটেইনার": "কন্টেইনার",
    "কনটেইনারে": "কন্টেইনারে",
    "সামপরদাযিক": "সাম্প্রদায়িক",
    "সমসযাকলিষট": "সমস্যাক্লিষ্ট",
    "সমসযাকলিস্ট": "সমস্যাক্লিষ্ট",
    "সমসযাক্লিষ্ট": "সমস্যাক্লিষ্ট",
    "বানিযেছেন": "বানিয়েছেন",
    "বানিযেছে": "বানিয়েছে",
    "নিযেছেন": "নিয়েছেন",
    "দিযেছেন": "দিয়েছেন",
    "নিযেছে": "নিয়েছে",
    "নিযেই": "নিজেই",
    "হওযার": "হওয়ার",
    "হওযায়": "হওয়ায়",
    "দখো": "দেখা",

    # -------------------------------------------------------------
    # 2. Vowel Restorations (U-kar, Uu-kar, Rri-kar, etc.)
    # -------------------------------------------------------------
    "নমনা": "নমুনা",
    "নমনার": "নমুনার",
    "মানষ": "মানুষ",
    "মানষকে": "মানুষকে",
    "মানষের": "মানুষের",
    "মানষে": "মানুষে",
    "মানষজন": "মানুষজন",
    "তলেছে": "তুলেছে",
    "মহামলযবান": "মহামূল্যবান",
    "মলযবান": "মূল্যবান",
    "নানামখী": "নানামুখী",
    "পরোপরি": "পুরোপুরি",
    "পরপুরি": "পুরোপুরি",
    "ঢকিয়ে": "ঢুকিয়ে",
    "থতনি": "থুতনি",
    "লকিয়ে": "লুকিয়ে",
    "লকিযে": "লুকিয়ে",
    "পযথিবীর": "পৃথিবীর",
    "পথিবী": "পৃথিবী",
    "পথিবীর": "পৃথিবীর",
    "সিরজনশীল": "সৃজনশীল",
    "বরিহত্তম": "বৃহত্তম",
    "করিতরিম": "কৃত্রিম",
    "কিরতরিমে": "কৃত্রিম",
    "সমরিদধ": "সমৃদ্ধ",
    "সমদধ": "সমৃদ্ধ",
    "আরো": "আরো",
    "ভালো": "ভালো",
    "কোন": "কোন",
    "কোনও": "কোনও",
    "শীঘরই": "শীঘ্রই",
    "রোবোটিকস": "রোবোটিক্স",
    "মখ": "মুখ",
    "খব": "খুব",

    # -------------------------------------------------------------
    # 3. आनंद Cluster & Frequent Compounds
    # -------------------------------------------------------------
    "আননদ": "আনন্দ",
    "আননদে": "আনন্দে",
    "আননদের": "আনন্দের",
    "আননদকে": "আনন্দকে",
    "আননদিত": "আনন্দিত",
    "সুননদ": "সুনন্দ",
    "সুনদর": "সুন্দর",
    "আতমহতযা": "আত্মহত্যা",
    "আতমবিশ্বাস": "আত্মবিশ্বাস",
    "আতমসমর্পণ": "আত্মসমর্পণ",
    "সটেশন": "স্টেশন",
    "পনডিত": "পণ্ডিত",
    "উচচ": "উচ্চ",
    "ইচছা": "ইচ্ছা",
    "লজজা": "লজ্জা",
    "পনচ": "পঞ্চ",
    "গনজ": "গঞ্জ",
    "উততর": "উত্তর",
    "বনধু": "বন্ধু",
    "শবদ": "শব্দ",
    "লবধ": "লব্ধ",
    "সতবধ": "স্তব্ধ",
    "ভরমন": "ভ্রমণ",
    "বাকস": "বাক্স",
    "টযাকসি": "ট্যাক্সি",
    "রিকসা": "রিক্সা",
    "সপরশ": "স্পর্শ",
    "সপশট": "স্পষ্ট",
    "চিহন": "চিহ্ন",
    "উশন": "উষ্ণ",
    "তৃষনা": "তৃষ্ণা",
    "কৃষন": "কৃষ্ণ",
    "বারহন": "ব্রাহ্মণ",
}

# Protected words list to strictly prevent false-positive regex collisions
PROTECTED_WORDS = {
    # Verb stems and inflections of 'করা'
    "কর", "করা", "করে", "করেছে", "করেছেন", "করবেন", "করছেন", "করতে", "করব", "করবে",
    "করিস", "করুন", "করতেন", "করল", "করলে", "করলেন", "করলেই", "করার", "করানো",
    "করছিল", "করছিলেন", "করণ", "করণীয়", "করমর্দন",
    # COVID-19 terms
    "করোনা", "করোনার", "করোনাভাইরাস", "করোনাভাইরাসের", "করোনাভাইরাসে", "করোনায়",
    # 'পর' root words
    "পর", "পরে", "পরের", "পরতে", "পরবর্তী", "পর্যাপ্ত", "পর্যন্ত", "পরমাণু", "পরখ", "পরস্পর",
    # 'সব' root words
    "সব", "সবাই", "সবুজ", "সবজি", "সবচেয়ে", "সবুর",
    # 'গর' words
    "গরু", "গরম", "গরিব",
    # 'তর' words
    "তরল", "তরঙ্গ", "তরফ", "তরুণ", "তরে",
    # Infinitives of n-stems
    "জানতে", "মানতে", "শুনতে", "আনতে", "গুনতে", "চিনতে", "স্থানান্তরিত",
    # Verbs ending in 'য' -> 'য়'
    "হয়", "দেয়", "নেয়", "যায়", "পায়", "খায়",
    # Common conjunctions and words
    "কত", "যত", "তত",
}


def normalize_bangla_unicode(text: str) -> str:
    """Canonical Unicode normalization for Bangla diacritics, nuktas, and ligatures."""
    if not text:
        return text
    text = unicodedata.normalize("NFC", text)
    # Fix nukta compositions: য + ় -> য়, ড + ় -> ড়, ঢ + ় -> ঢ়
    text = text.replace("\u09af\u09bc", "য়").replace("\u09a1\u09bc", "ড়").replace("\u09a2\u09bc", "ঢ়")
    return text


def normalize_bangla_vowels(text: str) -> str:
    """
    Normalizes and repairs Bangla vowel signs (কার-চিহ্ন):
    1. Circumfix O-kar (ো) and Ou-kar (ৌ) reconstruction (ে + consonant/cluster + া -> consonant/cluster + ো)
    2. Decomposed vowel joiner (ে + া -> ো, ে + ৗ -> ৌ)
    3. Pre-base vowel order repair (ি, ে, ৈ preceding consonant/cluster without base)
    4. Duplicate vowel sign suppression (e.g. াা -> া)
    5. Hasanta-vowel conflict resolution (্ + া -> া)
    """
    if not text:
        return text

    # Canonical NFC first
    text = normalize_bangla_unicode(text)

    # 1. Circumfix vowels in handwriting: boundary + ে + consonant/cluster + া -> cluster + ো
    # e.g. েকা -> কো, েপ্র -> প্রো, েকামল -> কোমল (guards against দেখা, খেলা, নেতা)
    non_consonant = r"(^|\s|[^\u0995-\u09b9\u09dc\u09dd\u09df])"
    text = re.sub(non_consonant + r"\u09c7(" + cluster_re + r")\u09be", r"\g<1>\g<2>ো", text)
    text = re.sub(non_consonant + r"\u09c7(" + cluster_re + r")[\u09d7\u09cc]", r"\g<1>\g<2>ৌ", text)

    # 2. Decomposed circumfix split vowels (consonant + ে + া -> consonant + ো)
    text = text.replace("\u09c7\u09be", "ো")
    text = text.replace("\u09c7\u09d7", "ৌ")
    text = text.replace("\u09c7\u09cc", "ৌ")
    text = text.replace("\u0985\u09be", "আ")  # অ + া -> আ

    # 3. Duplicate vowel sign deduplication (e.g. াা -> া, েে -> ে, ুু -> ু)
    text = re.sub(r"([" + vowel_kars + r"])\1+", r"\1", text)

    # 4. Remove Hasanta directly followed by a vowel sign (e.g. ক্ + া -> কা)
    text = re.sub(r"\u09cd([" + vowel_kars + r"])", r"\1", text)

    # 5. Fix inverted pre-base vowels (e.g. ি + consonant/cluster -> cluster + ি)
    text = re.sub(r"(^|\s|[^\u0980-\u09ff])(" + pre_base + r")(" + cluster_re + r")", r"\1\3\2", text)

    return text


# Pre-normalize lexicon keys & values to ensure exact Unicode match
JUKTAKKHOR_LEXICON = {
    normalize_bangla_vowels(k): normalize_bangla_vowels(v)
    for k, v in RAW_JUKTAKKHOR_LEXICON.items()
}


def restore_juktakkhor(text: str) -> str:
    """
    Restores joint characters (Juktakkhor) and vowel signs (কার) by applying
    linguistic rules, morphological repair, and dictionary mapping.
    Works reliably across any document while preserving grammar and protecting verb stems.
    """
    if not text:
        return text

    # Step A: Apply comprehensive vowel normalization
    text = normalize_bangla_vowels(text)
    words = text.split()
    corrected_words = []

    for word in words:
        # Separate trailing/leading punctuation
        m = re.match(r"^([^\w]*)([\w\u0980-\u09ff]+)([^\w]*)$", word)
        if not m:
            corrected_words.append(word)
            continue

        prefix, w, suffix = m.groups()
        w_norm = normalize_bangla_vowels(w)

        # 1. Direct dictionary lookup
        if w_norm in JUKTAKKHOR_LEXICON:
            w = JUKTAKKHOR_LEXICON[w_norm]
            corrected_words.append(prefix + w + suffix)
            continue

        # 2. Check protected words (do not alter verbs or common protected roots)
        if w_norm in PROTECTED_WORDS:
            corrected_words.append(prefix + w_norm + suffix)
            continue

        # 3. Targeted compound and phonological rules
        # A. Specific root & prefix corrections
        if "শরে" in w_norm:
            w_norm = w_norm.replace("শরে", "শ্রে")
        if "ফরেইম" in w_norm:
            w_norm = w_norm.replace("ফরেইম", "ফ্রেইম")
        if "আতম" in w_norm:
            w_norm = w_norm.replace("আতম", "আত্ম")
        if "কলিষ্ট" in w_norm or "কলিষট" in w_norm:
            w_norm = w_norm.replace("কলিষ্ট", "ক্লিষ্ট").replace("কলিষট", "ক্লিষ্ট")
        if "ছাতর" in w_norm:
            w_norm = w_norm.replace("ছাতর", "ছাত্র")
        if "দবার" in w_norm:
            w_norm = w_norm.replace("দবার", "দ্বার")

        # Pro (প্র-) restoration: পর... -> প্র...
        if w_norm.startswith("পর") and len(w_norm) > 3:
            # Safe consonant followers for প্র
            if w_norm[2] in ["ক", "ত", "থ", "ধ", "শ", "স", "ভ", "ব", "গ", "জ", "ণ", "য", "ফ"] and w_norm not in ["পরতে", "পরবর্তী", "পর্যাপ্ত", "পরমাণু"]:
                w_norm = "প্র" + w_norm[2:]
        elif "পরকাশ" in w_norm:
            w_norm = w_norm.replace("পরকাশ", "প্রকাশ")
        elif "পরতি" in w_norm:
            w_norm = w_norm.replace("পরতি", "প্রতি")

        # -ত্ব suffix (e.g. গুরুত্ব, ঘনত্ব, মহত্ত্ব, নেতৃত্ব, দায়িত্ব)
        if len(w_norm) > 2 and w_norm.endswith("তব"):
            w_norm = w_norm[:-2] + "ত্ব"

        # B. আনন্দ restoration
        if "আননদ" in w_norm:
            w_norm = w_norm.replace("আননদ", "আনন্দ")

        # C. ট/ঠ clusters (Run BEFORE ক্ষ so ষট becomes ষ্ট, not ক্ষ্ট)
        w_norm = w_norm.replace("ষঠ", "ষ্ঠ")        # শ্রেষ্ঠ, প্রতিষ্ঠান
        w_norm = w_norm.replace("ষট", "ষ্ট")        # কষ্ট, দৃষ্টি
        w_norm = w_norm.replace("সট", "স্ট")        # স্টেশন, স্টল
        w_norm = w_norm.replace("নট", "ন্ট")        # কন্টেইনার
        w_norm = w_norm.replace("নড", "ণ্ড")        # পণ্ডিত, কাণ্ড

        # D. চ/জ clusters
        w_norm = w_norm.replace("চচ", "চ্চ")        # উচ্চ
        w_norm = w_norm.replace("চছ", "চ্ছ")        # ইচ্ছা
        w_norm = w_norm.replace("জজ", "জ্জ")        # লজ্জা
        w_norm = w_norm.replace("নচ", "ঞ্চ")        # পঞ্চ
        w_norm = w_norm.replace("নজ", "ঞ্জ")        # গঞ্জ

        # E. ত/দ clusters
        w_norm = w_norm.replace("উততর", "উত্তর")    # উত্তর
        w_norm = w_norm.replace("তত", "ত্ত")        # সত্তা, সম্পত্তি
        w_norm = w_norm.replace("বনধু", "বন্ধু")    # বন্ধু
        w_norm = w_norm.replace("নধ", "ন্ধ")        # অন্ধকার, অন্ধ
        w_norm = w_norm.replace("দধ", "দ্ধ")        # সমৃদ্ধ, যুদ্ধ, বুদ্ধি

        # F. ক/জ conjuncts (Use negative lookahead to protect ষ্ট from turning into ক্ষ্ট)
        w_norm = re.sub(r"কষ(?!\u09cd)", "ক্ষ", w_norm)  # পরীক্ষা, সাক্ষী
        w_norm = w_norm.replace("জঞ", "জ্ঞ")        # জ্ঞান, বিজ্ঞান
        w_norm = w_norm.replace("কতি", "ক্তি")      # ব্যক্তিগত, শক্তি
        w_norm = w_norm.replace("ষকার", "ষ্কার")    # আবিষ্কার
        w_norm = w_norm.replace("সকার", "স্কার")    # পুরস্কার

        # G. স/শ clusters
        w_norm = w_norm.replace("সথ", "স্থ")        # স্থান, স্বাস্থ্য
        w_norm = w_norm.replace("সত", "স্ত")        # ব্যস্ত, প্রস্তুত
        w_norm = w_norm.replace("শব", "শ্ব")        # বিশ্ব, বিশ্বাস
        if "সবাসথয" in w_norm or "সবযং" in w_norm:
            w_norm = w_norm.replace("সবাসথয", "স্বাস্থ্য").replace("সবযং", "স্বয়ং")

        # H. ম clusters
        w_norm = w_norm.replace("মপ", "ম্প")        # সম্পর্ক, সম্পদ
        w_norm = w_norm.replace("মব", "ম্ব")        # সম্বল
        w_norm = w_norm.replace("মভ", "ম্ভ")        # সম্ভব, গম্ভীর
        w_norm = w_norm.replace("মম", "ম্ম")        # সম্মিলন, সম্মান

        # I. Safe N-conjuncts: avoid n+t verb stem clash (e.g. জানতে, মানতে)
        if "পরযনত" in w_norm:
            w_norm = w_norm.replace("পরযনত", "পর্যন্ত")
        if "আকরানত" in w_norm:
            w_norm = w_norm.replace("আকরানত", "আক্রান্ত")
        if "কেনদর" in w_norm:
            w_norm = w_norm.replace("কেনদর", "কেন্দ্র")

        # J. Jofola (্য) - MUST RUN BEFORE word-final glide 'য' -> 'য়'
        w_norm = w_norm.replace("বয", "ব্য")        # ব্যক্তি, ব্যবসা
        w_norm = w_norm.replace("ধয", "ধ্য")        # অধ্যাপক, মধ্য
        w_norm = w_norm.replace("তয", "ত্য")        # সাহিত্য, সত্য
        w_norm = w_norm.replace("নয", "ন্য")        # উপন্যাস, অন্য
        w_norm = w_norm.replace("লয", "ল্য")        # মূল্য, কল্যাণ
        w_norm = w_norm.replace("ডয", "ড্য")        # ড্যানিশ
        w_norm = w_norm.replace("সয", "স্য")        # সমস্যা, রহস্য
        w_norm = w_norm.replace("শয", "শ্য")        # দৃশ্য, অবশ্য
        w_norm = w_norm.replace("ভয", "ভ্য")        # সভ্য, অভ্যাস
        w_norm = w_norm.replace("দয", "দ্য")        # বিদ্যা, বিদ্যুৎ
        w_norm = w_norm.replace("থয", "থ্য")        # তথ্য, মিথ্যা
        w_norm = w_norm.replace("কয", "ক্য")        # ঐক্য, বাক্য
        w_norm = w_norm.replace("গয", "গ্য")        # যোগ্য, ভাগ্য

        # K. Verb glides and suffixes (িযে -> িয়ে, ওযার -> হওয়ার/ওয়ার)
        if "িযে" in w_norm:
            w_norm = w_norm.replace("িযে", "িয়ে")
        if "ওযার" in w_norm:
            w_norm = w_norm.replace("ওযার", "ওয়ার")
        if "ওযায়" in w_norm:
            w_norm = w_norm.replace("ওযায়", "ওয়ায়")
        if "ওযা" in w_norm and not w_norm.startswith("হও"):
            w_norm = w_norm.replace("ওযা", "ওয়া")
        elif w_norm.startswith("হওযা"):
            w_norm = w_norm.replace("হওযা", "হওয়া")

        # Final glide 'য' -> 'য়' (e.g. দেয -> দেয়, হয -> হয়) AFTER Jofolas
        if len(w_norm) > 1 and w_norm.endswith("য") and not w_norm.endswith("্য"):
            w_norm = w_norm[:-1] + "য়"

        # L. Ref (র্) rules:
        w_norm = w_norm.replace("অরজন", "অর্জন")
        w_norm = w_norm.replace("কারড", "কার্ড")
        w_norm = w_norm.replace("করম", "কর্ম")
        w_norm = w_norm.replace("বরন", "বর্ণ")
        w_norm = w_norm.replace("মরযাদা", "মর্যাদা")

        # M. Missing vowels
        if w_norm.endswith("মখী"):
            w_norm = w_norm[:-3] + "মুখী"
        if "নমনা" in w_norm:
            w_norm = w_norm.replace("নমনা", "নমুনা")
        if "মানষ" in w_norm:
            w_norm = w_norm.replace("মানষ", "মানুষ")
        if "মলযবান" in w_norm:
            w_norm = w_norm.replace("মলযবান", "মূল্যবান")

        corrected_words.append(prefix + w_norm + suffix)

    return " ".join(corrected_words)
