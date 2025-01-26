import streamlit as st
import requests
import json
import time

st.set_page_config(page_title="DeepSeek Chat", layout="wide")
st.title("🤖 DeepSeek API Chat")
st.caption("DeepSeek API를 사용한 스트리밍 채팅 인터페이스")

# DeepSeek API 키 설정
api_key = st.secrets["DEEPSEEK_API_KEY"]

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")

    model_version = st.selectbox(
        "모델 버전", ["deepseek-chat", "deepseek-coder"], index=0
    )
    max_tokens = st.number_input("최대 토큰", min_value=1, max_value=4096, value=1024)
    temperature = st.slider("창의성", 0.0, 2.0, 0.7, help="값이 높을수록 창의적인 응답")

# 세션 상태 관리
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"}
    ]

# 대화 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("메시지를 입력하세요..."):
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 어시스턴트 응답 생성
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        last_update = time.time()
        update_interval = 0.1

        try:
            with st.spinner("답변 생성 중..."):
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": model_version,
                    "messages": st.session_state.messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                }

                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=30,
                )

                response.raise_for_status()

                # 스트리밍 응답 처리
                for line in response.iter_lines():
                    if line:
                        try:
                            decoded_line = line.decode("utf-8").strip()

                            if not decoded_line:
                                continue
                            if decoded_line == "data: [DONE]":
                                break

                            if decoded_line.startswith("data:"):
                                json_str = decoded_line[5:].strip()
                                json_data = json.loads(json_str)

                                if json_data.get("choices"):
                                    delta = json_data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        chunk_content = delta["content"]
                                        full_response += chunk_content

                                        current_time = time.time()
                                        if (
                                            current_time - last_update
                                        ) > update_interval:
                                            message_placeholder.markdown(
                                                full_response + "▌"
                                            )
                                            last_update = current_time

                        except json.JSONDecodeError as e:
                            st.error(f"JSON 파싱 오류: {str(e)}")
                            continue
                        except Exception as e:
                            st.error(f"스트리밍 처리 오류: {str(e)}")
                            continue

                message_placeholder.markdown(full_response)

        except requests.exceptions.HTTPError as err:
            error_msg = f"API 요청 실패: {err}"
            if response.status_code == 401:
                error_msg = "인증 실패: 올바른 API 키를 입력해주세요"
            elif response.status_code == 429:
                error_msg = "요청 과다: 잠시 후 다시 시도해주세요"
            st.error(error_msg)
        except requests.exceptions.Timeout:
            st.error("요청 시간 초과: 네트워크 연결을 확인해주세요")
        except Exception as e:
            st.error(f"예상치 못한 오류: {str(e)}")

        if full_response:
            st.session_state.messages.append(
                {"role": "assistant", "content": full_response}
            )

    if len(st.session_state.messages) > 20:
        st.session_state.messages = st.session_state.messages[-10:]
