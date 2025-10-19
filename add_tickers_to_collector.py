"""
data_collector.py에 추가 종목을 자동으로 병합하는 스크립트
"""

# 추가할 종목 리스트
additional_tickers = [
    # OTC Markets - 고거래량 (48개)
    'HQGE', 'GVSI', 'LTUM', 'WNFT', 'IFXY', 'GDET',
    'DUTV', 'MINE', 'TSNP', 'TLSS', 'ABML',
    'MNGG', 'MYDX', 'PJET', 'HEMP', 'MCOA', 'GRCU',
    'TRTC', 'VATE', 'INND', 'VDRM', 'ECEZ', 'TAUG',
    'PVDG', 'CLSH', 'VPER', 'FDBL', 'FDCT',
    'EVSV',

    # AI & 양자컴퓨팅 2024-2025 (20개)
    'QBTS', 'DTST', 'CXAI', 'VTEX',
    'SPIR', 'PATH', 'NCNO', 'DOCN', 'RSKD', 'BRZE',
    'AMBA', 'SMTC', 'FORM', 'LITE', 'HIMX',
    'UCTT', 'MKSI',

    # 바이오테크 임상시험 (주요 100개만 선택)
    'ABEO', 'ACRS', 'ADVM', 'AGIO', 'ALNA',
    'ALNY', 'ALPN', 'ANIK', 'APLS', 'APLT',
    'APRE', 'ARAV', 'ARCT', 'ARGX', 'ASMB',
    'AUPH', 'AVEO', 'AVIR', 'AVXL', 'AXSM',
    'BDTX', 'BHVN', 'BIIB', 'BPMC', 'BTAI',
    'BYSI', 'CARA', 'CLDX', 'CMMB', 'CNTA',
    'CORT', 'CRNX', 'CRVS', 'CTMX', 'CVAC',
    'CYCN', 'CYTK', 'DAWN', 'DNLI', 'DSGN',
    'DVAX', 'EIGR', 'ELVN', 'EPIX', 'ERAS',
    'ESPR', 'ETNB', 'EVLO', 'FDMT',
    'FOLD', 'FGEN', 'FMTX', 'GERN', 'GILD',
    'GLPG', 'GLUE', 'GOSS', 'HALO', 'HGEN',
    'HRTX', 'IGMS', 'IMAB', 'IMCR', 'IMGN',
    'IMMP', 'INCY', 'IONS', 'IOVA', 'IRWD',
    'ITCI', 'JANX', 'KALA', 'KALV',
    'KRYS', 'KYMR', 'KZIA', 'LEGN', 'LIFE',
    'LIPO', 'LTRN', 'LUNA', 'LYEL', 'MCRB',
    'MDGL', 'MGNX', 'MNKD', 'MOLN', 'MRUS',
    'MTEM', 'MYGN', 'NARI', 'NBIX', 'NCNA',
    'NKTX', 'NMTC', 'NTRA',
    'NUVB', 'NVTA', 'NWBO', 'OMER',
    'ONCT', 'ONEM', 'ORTX', 'OSPN', 'PCVX',
    'PDFS', 'PGEN', 'PHAT', 'PIRS', 'PRTK',
    'PRVB', 'PTCT', 'PTGX',

    # Recent IPO 2023-2025 (15개)
    'RDDT', 'DASH', 'RBLX',
    'DIDI', 'GRAB', 'ASTS', 'BROS', 'FROG',
    'GLBE', 'WYNN', 'ZS', 'CRWD', 'DDOG',
    'NET', 'SNOW', 'U',

    # EV & 그린에너지 (20개)
    'PLUG', 'FCEL', 'BE', 'BLDP', 'CLNE',
    'ENPH', 'SEDG', 'RUN', 'CSIQ',
    'JKS', 'SPWR', 'MAXN', 'ARRY',
    'NEP', 'AY', 'CWEN', 'BEPC', 'ORA',

    # 크립토/블록체인 (10개 - 중복 제외)
    'WULF', 'CORZ', 'BTDR', 'DGHI',

    # SPAC & De-SPAC (15개)
    'PSFE', 'OPEN', 'GENI', 'DKNG',
    'BODY', 'BARK', 'TALK', 'ME',
    'OUST', 'LAZR', 'VLDR', 'MKFG',
    'DM', 'NNDM', 'SLDP',

    # 대마초 & 환각제 (10개 - 중복 제외)
    'HEXO', 'OGI', 'MSOS', 'YOLO',
    'CMPS', 'ATAI', 'MNMD', 'FTRP', 'NUMI',
]

print("=" * 100)
print("data_collector.py 종목 추가 스크립트")
print("=" * 100)

print(f"\n추가할 종목 수: {len(additional_tickers)}개")
print(f"중복 제거 전 총 종목: {len(additional_tickers)}개")

# 중복 제거
additional_tickers = list(set(additional_tickers))
print(f"중복 제거 후 총 종목: {len(additional_tickers)}개")

# 파일 읽기
file_path = 'src/data_collector.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# penny_stocks 리스트 찾기
import re

# 리스트 끝 찾기 (마지막 ] 전에 추가)
# 패턴: ] 다음에 공백과 함께 오는 줄 찾기
pattern = r"(\s+'CDTX',.*?\n\s+\])"

# 추가할 내용 생성
additional_lines = "\n\n            # ===== 추가 종목 (자동 추가됨) =====\n"

# 카테고리별로 그룹화
categories = {
    'OTC Markets 고거래량': ['HQGE', 'GVSI', 'LTUM', 'WNFT', 'IFXY', 'GDET',
        'DUTV', 'MINE', 'TSNP', 'TLSS', 'ABML',
        'MNGG', 'MYDX', 'PJET', 'HEMP', 'MCOA', 'GRCU',
        'TRTC', 'VATE', 'INND', 'VDRM', 'ECEZ', 'TAUG',
        'PVDG', 'CLSH', 'VPER', 'FDBL', 'FDCT', 'EVSV'],

    'AI & 양자컴퓨팅 확장': ['QBTS', 'DTST', 'CXAI', 'VTEX',
        'SPIR', 'PATH', 'NCNO', 'DOCN', 'RSKD', 'BRZE',
        'AMBA', 'SMTC', 'FORM', 'LITE', 'HIMX',
        'UCTT', 'MKSI'],

    '바이오테크 임상시험 확장': ['ABEO', 'ACRS', 'ADVM', 'AGIO', 'ALNA',
        'ALNY', 'ALPN', 'ANIK', 'APLS', 'APLT',
        'APRE', 'ARAV', 'ARCT', 'ARGX', 'ASMB',
        'AUPH', 'AVEO', 'AVIR', 'AVXL', 'AXSM',
        'BDTX', 'BHVN', 'BIIB', 'BPMC', 'BTAI',
        'BYSI', 'CARA', 'CLDX', 'CMMB', 'CNTA',
        'CORT', 'CRNX', 'CRVS', 'CTMX', 'CVAC',
        'CYCN', 'CYTK', 'DAWN', 'DNLI', 'DSGN',
        'DVAX', 'EIGR', 'ELVN', 'EPIX', 'ERAS',
        'ESPR', 'ETNB', 'EVLO', 'FDMT',
        'FOLD', 'FGEN', 'FMTX', 'GERN', 'GILD',
        'GLPG', 'GLUE', 'GOSS', 'HALO', 'HGEN',
        'HRTX', 'IGMS', 'IMAB', 'IMCR', 'IMGN',
        'IMMP', 'INCY', 'IONS', 'IOVA', 'IRWD',
        'ITCI', 'JANX', 'KALA', 'KALV',
        'KRYS', 'KYMR', 'KZIA', 'LEGN', 'LIFE',
        'LIPO', 'LTRN', 'LUNA', 'LYEL', 'MCRB',
        'MDGL', 'MGNX', 'MNKD', 'MOLN', 'MRUS',
        'MTEM', 'MYGN', 'NARI', 'NBIX', 'NCNA',
        'NKTX', 'NMTC', 'NTRA',
        'NUVB', 'NVTA', 'NWBO', 'OMER',
        'ONCT', 'ONEM', 'ORTX', 'OSPN', 'PCVX',
        'PDFS', 'PGEN', 'PHAT', 'PIRS', 'PRTK',
        'PRVB', 'PTCT', 'PTGX'],

    'Recent IPO 2023-2025': ['RDDT', 'DASH', 'RBLX',
        'DIDI', 'GRAB', 'ASTS', 'BROS', 'FROG',
        'GLBE', 'WYNN', 'ZS', 'CRWD', 'DDOG',
        'NET', 'SNOW', 'U'],

    'EV & 그린에너지 확장': ['PLUG', 'FCEL', 'BE', 'BLDP', 'CLNE',
        'ENPH', 'SEDG', 'RUN', 'CSIQ',
        'JKS', 'SPWR', 'MAXN', 'ARRY',
        'NEP', 'AY', 'CWEN', 'BEPC', 'ORA'],

    '크립토/블록체인 확장': ['WULF', 'CORZ', 'BTDR', 'DGHI'],

    'SPAC & De-SPAC': ['PSFE', 'OPEN', 'GENI', 'DKNG',
        'BODY', 'BARK', 'TALK', 'ME',
        'OUST', 'LAZR', 'VLDR', 'MKFG',
        'DM', 'NNDM', 'SLDP'],

    '대마초 & 환각제 확장': ['HEXO', 'OGI', 'MSOS', 'YOLO',
        'CMPS', 'ATAI', 'MNMD', 'FTRP', 'NUMI'],
}

for category, tickers in categories.items():
    additional_lines += f"\n            # {category} ({len(tickers)}개)\n"

    # 한 줄에 6개씩 배치
    for i in range(0, len(tickers), 6):
        batch = tickers[i:i+6]
        ticker_str = ', '.join([f"'{t}'" for t in batch])
        additional_lines += f"            {ticker_str},\n"

# 패턴 찾기 및 교체
match = re.search(pattern, content, re.DOTALL)
if match:
    # 마지막 ] 앞에 추가
    insert_pos = match.end() - 2  # ] 앞 위치

    # 새로운 내용 생성
    new_content = content[:insert_pos] + additional_lines + content[insert_pos:]

    # 백업 생성
    import shutil
    backup_path = 'src/data_collector_backup.py'
    shutil.copy(file_path, backup_path)
    print(f"\n원본 백업 완료: {backup_path}")

    # 파일 쓰기
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✓ {file_path} 업데이트 완료!")
    print(f"✓ 총 {len(additional_tickers)}개 종목 추가됨")

    # 카테고리별 통계
    print("\n[카테고리별 추가 종목]")
    for category, tickers in categories.items():
        print(f"  - {category}: {len(tickers)}개")

    print("\n" + "=" * 100)
    print("다음 단계:")
    print("=" * 100)
    print("""
1. python download_3year_data.py
   - 새로운 종목의 3년치 데이터 다운로드
   - 예상 시간: 1-2시간

2. python train_god_model.py
   - 확장된 데이터로 God 모델 재학습
   - 예상 시간: 3-4시간

3. python backtest_god_model.py
   - 새로운 모델 백테스트
   - 성능 비교

4. 성능 비교:
   - 기존: 232개 종목, 73.5% 성공률
   - 신규: ~450개 종목, 성능 향상 기대
""")

else:
    print("오류: penny_stocks 리스트를 찾을 수 없습니다.")
    print("수동으로 종목을 추가해주세요.")

    print("\n[추가할 종목 리스트]")
    print("-" * 100)
    for category, tickers in categories.items():
        print(f"\n# {category}")
        for i in range(0, len(tickers), 6):
            batch = tickers[i:i+6]
            print(", ".join([f"'{t}'" for t in batch]) + ",")

print("\n" + "=" * 100)
