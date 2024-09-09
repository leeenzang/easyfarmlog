import arrow
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .serializers import WeatherInfoSerializer
from common.weather import fetch_data_from_kma
from farmlog.models import FarmLog
from farmlog.serializers import FarmLogSerializer
from django.utils import timezone
from django.db.models import Q

# 하늘 상태 및 강수 형태 매핑 (필요에 따라 수정 가능)
STATUS_OF_SKY = {
    '1': '맑음',
    '3': '구름 많음',
    '4': '흐림'
}

STATUS_OF_PRECIPITATION = {
    '0': '없음',
    '1': '비',
    '2': '비/눈',
    '3': '눈',
    '4': '소나기'
}

class PreviousRecordsView(APIView):
    def get(self, request):
        today = timezone.now().date()

        # 1년 전, 2년 전 날짜 계산 (년도만 -1, -2 해서 계산)
        one_year_ago = today.replace(year=today.year - 1)
        two_years_ago = today.replace(year=today.year - 2)

        # 1년 전과 2년 전 기록 불러오기
        records_one_year_ago = FarmLog.objects.filter(date=one_year_ago, user=request.user)
        records_two_years_ago = FarmLog.objects.filter(date=two_years_ago, user=request.user)

        # 시리얼라이저로 데이터 직렬화
        records_one_year_ago_serialized = FarmLogSerializer(records_one_year_ago, many=True)
        records_two_years_ago_serialized = FarmLogSerializer(records_two_years_ago, many=True)

        return Response({
            'records_one_year_ago': records_one_year_ago_serialized.data,
            'records_two_years_ago': records_two_years_ago_serialized.data,
        }, status=status.HTTP_200_OK)

class DashboardView(APIView):
    def get(self, request):
        # 현재 날짜 (KST 기준)
        current_time_kst = arrow.now('Asia/Seoul')
        date_format = "YYYY년 MM월 DD일 dddd"
        date_of_today = current_time_kst.format(date_format, locale="ko_kr")

        # 날씨 정보
        sky = fetch_data_from_kma(current_time_kst, 'SKY', '0500')
        precipitation = fetch_data_from_kma(current_time_kst, 'PTY', '0500')
        lowest_temp_of_today = fetch_data_from_kma(current_time_kst, 'TMP', '0600')
        highest_temp_of_today = fetch_data_from_kma(current_time_kst, 'TMP', '1500')
        precipitation_probability = fetch_data_from_kma(current_time_kst, 'POP', '0500')  # 강수확률
        humidity = fetch_data_from_kma(current_time_kst, 'REH', '0500')  # 습도

        if (sky is None or precipitation is None or
            lowest_temp_of_today is None or highest_temp_of_today is None or
            precipitation_probability is None or humidity is None):
            return Response({"error": "날씨 정보를 가져오지 못했습니다. 😢"}, status=500)

        weather_of_today = f"{STATUS_OF_SKY.get(sky, '알 수 없음')} (강수: {STATUS_OF_PRECIPITATION.get(precipitation, '알 수 없음')})"
        weather_info = {
            'current_weather': weather_of_today,
            'highest_temp': highest_temp_of_today,
            'lowest_temp': lowest_temp_of_today,
            'date_of_today': date_of_today,
            'precipitation_probability': precipitation_probability,  # 강수확률 추가
            'humidity': humidity  # 습도 추가
        }

        serializer = WeatherInfoSerializer(weather_info)
        return Response(serializer.data)