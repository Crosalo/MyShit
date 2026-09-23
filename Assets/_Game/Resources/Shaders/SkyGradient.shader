Shader "Aether/SkyGradient"
{
    Properties
    {
        _TopColor ("Oben", Color) = (0.3,0.4,0.9,1)
        _HorizonColor ("Horizont", Color) = (1,0.7,0.8,1)
        _BottomColor ("Unten", Color) = (0.2,0.15,0.3,1)
    }
    SubShader
    {
        Tags { "Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox" }
        Cull Off ZWrite Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            fixed4 _TopColor, _HorizonColor, _BottomColor;
            struct v2f { float4 pos : SV_POSITION; float3 dir : TEXCOORD0; };
            v2f vert (float4 vertex : POSITION) { v2f o; o.pos = UnityObjectToClipPos(vertex); o.dir = vertex.xyz; return o; }
            fixed4 frag (v2f i) : SV_Target
            {
                float h = normalize(i.dir).y;
                return h > 0 ? lerp(_HorizonColor, _TopColor, pow(h, 0.6)) : lerp(_HorizonColor, _BottomColor, pow(-h, 0.5));
            }
            ENDCG
        }
    }
}
