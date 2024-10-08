# views.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.dateparse import parse_date
import arrow
from .models import FarmLog
from .serializers import FarmLogSerializer
from common.lunar_api import get_lunar_date
from common.weather import fetch_data_from_kma  # import fetch_data_from_kma
import xml.etree.ElementTree as ET

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

class FarmLogListCreateView(generics.ListCreateAPIView):
    queryset = FarmLog.objects.all()
    serializer_class = FarmLogSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        date = serializer.validated_data['date']
        try:
            lunar_date = get_lunar_date(date.year, date.month, date.day)
            lunar_date_str = f"{lunar_date['lunar_year']}-{lunar_date['lunar_month']}-{lunar_date['lunar_day']}"
        except Exception as e:
            lunar_date_str = None  # Lunar date를 가져올 수 없을 때 처리

        # 날씨 정보 가져오기
        current_time_kst = arrow.get(date.year, date.month, date.day).to('Asia/Seoul')
        sky = fetch_data_from_kma(current_time_kst, 'SKY', '0500')
        precipitation = fetch_data_from_kma(current_time_kst, 'PTY', '0500')
        lowest_temp_of_today = fetch_data_from_kma(current_time_kst, 'TMP', '0600')
        highest_temp_of_today = fetch_data_from_kma(current_time_kst, 'TMP', '1500')

        weather_of_today = f"{STATUS_OF_SKY.get(sky, '알 수 없음')} (강수: {STATUS_OF_PRECIPITATION.get(precipitation, '알 수 없음')})"
        
        serializer.save(
            user=self.request.user,
            lunar_date=lunar_date_str,
            max_temp=highest_temp_of_today,
            min_temp=lowest_temp_of_today,
            weather=weather_of_today
        )

class FarmLogListView(generics.ListAPIView):
    serializer_class = FarmLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FarmLog.objects.filter(user=self.request.user)
    
class FarmLogDetailView(generics.RetrieveAPIView):
    queryset = FarmLog.objects.all()
    serializer_class = FarmLogSerializer
    permission_classes = [IsAuthenticated]


class CalculateLunarDateView(APIView):
    def post(self, request, *args, **kwargs):
        date_str = request.data.get('date')
        if not date_str:
            return Response({'error': 'Date is required'}, status=status.HTTP_400_BAD_REQUEST)

        solar_date = parse_date(date_str)
        if not solar_date:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lunar_date = get_lunar_date(solar_date.year, solar_date.month, solar_date.day)
            lunar_date_str = f"{lunar_date['lunar_year']}-{lunar_date['lunar_month']}-{lunar_date['lunar_day']}"
        except Exception as e:
            return Response({'error': 'Failed to calculate lunar date'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'lunar_date': lunar_date_str}, status=status.HTTP_200_OK)