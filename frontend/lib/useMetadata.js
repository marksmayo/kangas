import { useContext, useState, useEffect, useRef } from 'react';
import { ConfigContext } from '../components/Cells/ClientContext.client';

/* 
Kangas fetches assets and metadata in different ways depending on the circumstance. Wherever possible,
Kangas fetches on the server-side, making use of React Server Components. However, in situations where
client-side fetching is necessary—like in the <Canvas /> component, Kangas has two different modes of 
client-side fetching, depending on environment. When running inside an iframe, like in a Colab/Jupyter environment,
Kangas performs fetches by posting a message to the parent frame, which handles data fetching and responds.
Outside of an iframe, Kangas will fetch against the relevant endpoint directly, in some situations making use
of Next.js api routes
*/

const useMetadata = (dgid, assetId) => {
    const { isIframe, apiUrl } = useContext(ConfigContext);
    const [metadata, setMetadata] = useState();
    const listenerAttached = useRef(false);

    useEffect(() => {
        // Handle Iframes (Jupyter notebooks/Colab etc.)

        // Attach metadata listener
        if (isIframe && !listenerAttached.current) {
            window.addEventListener("message", e => {
                const { messageType, ...data } = e.data;
                if (messageType === 'metadata') {
                    setMetadata(data);
                }
            }, false);
            listenerAttached.current = true;
        }

        if (isIframe) {
            // Fire postMessage request for metadata
            if (assetId && dgid) {
                window.parent.postMessage({dgid, assetId, type: 'metadata'}, "*");
            }
        }

        // Non-iframe fetching
        else {
            fetch(`/api/metadata?${new URLSearchParams({
                assetId: assetId || new URL(url).searchParams.get('assetId'),
                dgid,
                url: `${apiUrl}/datagrid/asset-metadata`,
            })}`)
            .then((res) => res.json())
            .then((data) => setMetadata(JSON.parse(data)));

        }
    }, [dgid, assetId]);

    return metadata;
}

export default useMetadata;