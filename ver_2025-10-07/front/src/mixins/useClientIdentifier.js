import { ref, onMounted } from 'vue'

export function useClientIdentifier() {
  const localIP = ref('0.0.0.0')
  const userAgent = ref('')
  const uuid = ref('')

  const getLocalIP = () => {
    return new Promise((resolve) => {
      const pc = new RTCPeerConnection({ iceServers: [] });
      pc.createDataChannel('');

      pc.createOffer()
        .then(offer => pc.setLocalDescription(offer))
        .catch(() => resolve('0.0.0.0'));

      pc.onicecandidate = (event) => {
        if (!event || !event.candidate) return;

        const candidate = event.candidate.candidate;

        // ❗ 避免 mDNS，濾掉 .local 名稱
        if (candidate.includes('.local')) return;

        const ipMatch = candidate.match(/([0-9]{1,3}(\.[0-9]{1,3}){3})/);
        if (ipMatch) {
          resolve(ipMatch[1]);
          pc.close();
        }
      };

      setTimeout(() => resolve('0.0.0.0'), 2500);
    });
  };

  const generateUUID = () => {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11)
      .replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
      )
  }

  const loadClientInfo = async () => {
    localIP.value = await getLocalIP()

    userAgent.value = navigator.userAgent

    const stored = localStorage.getItem('client_uuid')
    if (stored) {
      uuid.value = stored
    } else {
      uuid.value = generateUUID()
      localStorage.setItem('client_uuid', uuid.value)
    }
  }

  onMounted(() => {
    loadClientInfo()
  })

  return {
    localIP,
    userAgent,
    uuid
  }
}

