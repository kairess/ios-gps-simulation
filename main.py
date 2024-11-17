from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
import time
import math
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

class WalkingSimulator:
    def __init__(self, host, port, walking_speed_kmh=4.0):
        self.walking_speed_kmh = walking_speed_kmh
        self.host = host
        self.port = port

        # 걸음 속도에 따른 update_interval 계산
        steps_per_km = 1333  # 1km당 평균 걸음 수 (0.75m 보폭 기준)
        steps_per_hour = steps_per_km * walking_speed_kmh  # 시간당 걸음 수
        steps_per_second = steps_per_hour / 3600  # 초당 걸음 수
        self.update_interval = 1 / steps_per_second  # 한 걸음당 소요 시간(초)
        """
        계산 예시 (4km/h 기준):
        - 1km당 걸음 수: 1333걸음 (0.75m 보폭)
        - 시간당 걸음 수: 1333 * 4 = 5332걸음
        - 초당 걸음 수: 5332 / 3600 ≈ 1.48걸음
        - update_interval: 1 / 1.48 ≈ 0.67초
        """

    @classmethod
    async def create(cls, host, port, walking_speed_kmh=4.0):
        self = cls(host, port, walking_speed_kmh)

        rsd = RemoteServiceDiscoveryService((self.host, self.port))
        await rsd.connect()

        self.dvt = DvtSecureSocketProxyService(rsd)
        self.dvt.perform_handshake()
        self.simulation = LocationSimulation(self.dvt)

        return self

    def cleanup(self):
        """리소스 정리"""
        try:
            if hasattr(self, 'simulation'):
                self.simulation.clear()
            if hasattr(self, 'dvt'):
                self.dvt.close()
        except Exception as e:
            print(f"정리 중 오류 발생: {str(e)}")

    def calculate_distance(self, start_pos, end_pos):
        """두 지점 간의 거리를 계산 (Haversine 공식, km 단위)"""
        lat1, lon1 = start_pos
        lat2, lon2 = end_pos
        R = 6371  # 지구의 반경 (km)
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    def generate_intermediate_points(self, start_pos, end_pos):
        """시작점과 끝점 사이의 중간 지점들을 생성"""
        start_lat, start_lon = start_pos
        end_lat, end_lon = end_pos

        distance = self.calculate_distance(start_pos, end_pos)
        walking_time = distance / self.walking_speed_kmh  # 시간(hour)
        total_steps = int(walking_time * 3600 / self.update_interval)  # 초당 스텝 수로 변환

        if total_steps < 1:
            return [(end_lat, end_lon)]

        points = []
        for i in range(total_steps + 1):
            fraction = i / total_steps
            lat = start_lat + (end_lat - start_lat) * fraction
            lon = start_lon + (end_lon - start_lon) * fraction
            points.append((lat, lon))
        return points

    def simulate_walking(self, start_pos, end_pos):
        """도보 시뮬레이션 실행"""
        try:
            # 시작 시간 기록
            start_time = datetime.now()
            distance = self.calculate_distance(start_pos, end_pos)
            walking_time_hours = distance / self.walking_speed_kmh
            estimated_end_time = start_time + timedelta(hours=walking_time_hours)

            print(f"\n도보 시뮬레이션 시작:")
            print(f"이동 속도: {self.walking_speed_kmh}km/h")
            print(f"한 걸음당 소요 시간: {self.update_interval:.2f}초\n")

            print(f"이동 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"예상 도착 시간: {estimated_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"예상 소요 시간: {walking_time_hours:.1f}시간 ({int(walking_time_hours * 60)}분)\n")

            print(f"시작 지점: {start_pos}")
            print(f"도착 지점: {end_pos}\n")

            points = self.generate_intermediate_points(start_pos, end_pos)
            total_steps = len(points)

            print(f"총 이동 거리: {distance:.2f}km")
            print(f"예상 걸음 수: {total_steps}\n")

            for i, (lat, lon) in enumerate(points, 1):
                remaining_steps = total_steps - i
                print(f"\r진행률: {i}/{total_steps} (남은 걸음 수: {remaining_steps})", end="")
                self.simulation.set(lat, lon)
                time.sleep(self.update_interval)

            # 실제 종료 시간 기록
            end_time = datetime.now()
            actual_duration = (end_time - start_time).total_seconds() / 3600  # 시간 단위

            print(f"\n도보 시뮬레이션 완료")
            print(f"실제 소요 시간: {actual_duration:.1f}시간 ({int(actual_duration * 60)}분)")
            print(f"종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            print(f"오류 발생: {str(e)}")
        finally:
            self.cleanup()

    def simulate_walking_multiple_points(self, points):
        """여러 지점을 순차적으로 이동하는 도보 시뮬레이션 실행"""
        try:
            start_time = datetime.now()
            total_distance = 0

            # 총 이동 거리 계산
            for i in range(len(points)-1):
                total_distance += self.calculate_distance(points[i], points[i+1])

            total_walking_time_hours = total_distance / self.walking_speed_kmh
            estimated_end_time = start_time + timedelta(hours=total_walking_time_hours)

            print(f"\n다중 경로 도보 시뮬레이션 시작:")
            print(f"총 이동 거리: {total_distance:.2f}km")
            print(f"이동 속도: {self.walking_speed_kmh}km/h")
            print(f"한 걸음당 소요 시간: {self.update_interval:.2f}초\n")
            print(f"총 경유지 수: {len(points)}개")
            print(f"이동 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"예상 도착 시간: {estimated_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"예상 총 소요 시간: {total_walking_time_hours:.1f}시간 ({int(total_walking_time_hours * 60)}분)\n")

            # 각 구간별 이동
            for i in range(len(points)-1):
                current_pos = points[i]
                next_pos = points[i+1]
                print(f"\n[구간 {i+1}/{len(points)-1}]")
                print(f"출발: {current_pos}")
                print(f"도착: {next_pos}")

                segment_points = self.generate_intermediate_points(current_pos, next_pos)
                segment_distance = self.calculate_distance(current_pos, next_pos)
                print(f"구간 거리: {segment_distance:.2f}km")

                for j, (lat, lon) in enumerate(segment_points, 1):
                    print(f"\r현재 구간 진행률: {j}/{len(segment_points)}", end="")
                    self.simulation.set(lat, lon)
                    time.sleep(self.update_interval)

            end_time = datetime.now()
            actual_duration = (end_time - start_time).total_seconds() / 3600

            print(f"\n\n도보 시뮬레이션 완료")
            print(f"총 이동 거리: {total_distance:.2f}km")
            print(f"실제 소요 시간: {actual_duration:.1f}시간 ({int(actual_duration * 60)}분)")
            print(f"종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            print(f"오류 발생: {str(e)}")
        finally:
            self.cleanup()

    def parse_gpx_points(self, gpx_file):
        """GPX 파일에서 트랙포인트들을 추출"""
        tree = ET.parse(gpx_file)
        root = tree.getroot()

        # XML 네임스페이스 처리
        ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}

        points = []
        for trkpt in root.findall('.//gpx:trkpt', ns):
            lat = float(trkpt.get('lat'))
            lon = float(trkpt.get('lon'))
            points.append((lat, lon))

        return points

    def simulate_walking_with_gpx(self, gpx_file):
        """GPX 파일을 기반으로 도보 시뮬레이션 실행"""
        try:
            # GPX 파일에서 경로점 추출
            points = self.parse_gpx_points(gpx_file)

            if not points:
                raise ValueError("GPX 파일에서 유효한 경로점을 찾을 수 없습니다.")

            # 시작 시간 기록
            start_time = datetime.now()

            # 총 이동 거리 계산
            total_distance = sum(
                self.calculate_distance(points[i], points[i+1])
                for i in range(len(points)-1)
            )

            total_walking_time_hours = total_distance / self.walking_speed_kmh
            estimated_end_time = start_time + timedelta(hours=total_walking_time_hours)

            print(f"\nGPX 기반 도보 시뮬레이션 시작:")
            print(f"총 경로점 수: {len(points)}개")
            print(f"총 이동 거리: {total_distance:.2f}km")
            print(f"이동 속도: {self.walking_speed_kmh}km/h")
            print(f"한 걸음당 소요 시간: {self.update_interval:.2f}초\n")
            print(f"이동 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"예상 도착 시간: {estimated_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"예상 총 소요 시간: {total_walking_time_hours:.1f}시간 ({int(total_walking_time_hours * 60)}분)\n")

            # 각 구간별 이동
            total_steps = 0
            total_segments = len(points) - 1

            for i in range(total_segments):
                current_pos = points[i]
                next_pos = points[i+1]

                print(f"\n\n[구간 {i+1}/{total_segments}]")
                print(f"현재 위치: {current_pos}")
                print(f"다음 위치: {next_pos}")

                segment_distance = self.calculate_distance(current_pos, next_pos)
                print(f"구간 거리: {segment_distance:.2f}km")

                # 현재 구간의 중간 지점들 생성
                segment_points = self.generate_intermediate_points(current_pos, next_pos)
                total_steps += len(segment_points)

                for j, (lat, lon) in enumerate(segment_points, 1):
                    print(f"\r현재 구간 진행률: {j}/{len(segment_points)} "
                          f"(전체 진행률: {((i*100)/total_segments):.1f}%)", end="")
                    self.simulation.set(lat, lon)
                    time.sleep(self.update_interval)

            end_time = datetime.now()
            actual_duration = (end_time - start_time).total_seconds() / 3600

            print(f"\n\n도보 시뮬레이션 완료")
            print(f"총 이동 거리: {total_distance:.2f}km")
            print(f"총 걸음 수: {total_steps}걸음")
            print(f"실제 소요 시간: {actual_duration:.1f}시간 ({int(actual_duration * 60)}분)")
            print(f"종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            print(f"오류 발생: {str(e)}")
        finally:
            self.cleanup()

async def main(rsd_address, rsd_port):
    while True:
        simulator = await WalkingSimulator.create(
            host=rsd_address,
            port=rsd_port,
            walking_speed_kmh=5.0
        )

        # GPX 파일을 기반으로 도보 시뮬레이션
        simulator.simulate_walking_with_gpx('test.gpx')

    # 수동으로 경유지 설정하여 도보 시뮬레이션
    # WAYPOINTS = [
    #     (37.52408867459685, 126.87672439031735),  # 시작점: 오목교역
    #     (37.52644060524283, 126.86545735223037),  # 중간 경유지1: 목동역
    #     (37.52779777486183, 126.87385832232388),  # 중간 경유지2: 오목공원
    #     (37.52408867459685, 126.87672439031735)   # 시작점으로 돌아오기
    # ]

    # simulator.simulate_walking_multiple_points(WAYPOINTS)

if __name__ == "__main__":
    import asyncio
    import sys
    asyncio.run(main(rsd_address=sys.argv[1], rsd_port=sys.argv[2]))
