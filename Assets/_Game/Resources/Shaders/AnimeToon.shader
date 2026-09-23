Shader "Aether/AnimeToon"
{
    Properties
    {
        _Color ("Farbe", Color) = (1,1,1,1)
        _MainTex ("Textur", 2D) = "white" {}
        _ShadeColor ("Schattenfarbe", Color) = (0.7,0.65,0.85,1)
        _ShadeThreshold ("Schattengrenze", Range(-1,1)) = 0.1
        _ShadeSoftness ("Weichheit", Range(0.001,0.5)) = 0.04
        _RimIntensity ("Randlicht", Range(0,1)) = 0.3
        _Emission ("Leuchten", Range(0,1)) = 0
        _OutlineColor ("Outline", Color) = (0.12,0.1,0.16,1)
        _OutlineWidth ("Outline-Breite", Range(0,0.02)) = 0.004
        _Flash ("Treffer-Blitz", Range(0,1)) = 0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Pass
        {
            Tags { "LightMode"="ForwardBase" }
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fwdbase
            #include "UnityCG.cginc"
            #include "Lighting.cginc"
            #include "AutoLight.cginc"
            sampler2D _MainTex; float4 _MainTex_ST;
            fixed4 _Color, _ShadeColor;
            float _ShadeThreshold, _ShadeSoftness, _RimIntensity, _Emission, _Flash;
            struct appdata { float4 vertex : POSITION; float3 normal : NORMAL; float2 uv : TEXCOORD0; };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; float3 n : TEXCOORD1; float3 wp : TEXCOORD2; SHADOW_COORDS(3) };
            v2f vert (appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.uv = TRANSFORM_TEX(v.uv, _MainTex);
                o.n = UnityObjectToWorldNormal(v.normal); o.wp = mul(unity_ObjectToWorld, v.vertex).xyz; TRANSFER_SHADOW(o); return o; }
            fixed4 frag (v2f i) : SV_Target
            {
                float3 n = normalize(i.n);
                float3 l = normalize(_WorldSpaceLightPos0.xyz);
                float3 v = normalize(_WorldSpaceCameraPos - i.wp);
                float lit = smoothstep(_ShadeThreshold - _ShadeSoftness, _ShadeThreshold + _ShadeSoftness, dot(n, l));
                lit *= step(0.5, SHADOW_ATTENUATION(i));
                fixed3 albedo = tex2D(_MainTex, i.uv).rgb * _Color.rgb;
                fixed3 col = albedo * lerp(_ShadeColor.rgb, 1, lit) * _LightColor0.rgb + albedo * ShadeSH9(float4(n,1)) * 0.25;
                col += pow(1 - saturate(dot(n, v)), 3.5) * _RimIntensity * lit;
                col = lerp(col, albedo * 1.2, _Emission);
                return fixed4(lerp(col, 1, _Flash), 1);
            }
            ENDCG
        }
        Pass
        {
            Name "OUTLINE"
            Cull Front
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            float _OutlineWidth, _Flash; fixed4 _OutlineColor;
            struct appdata { float4 vertex : POSITION; float3 normal : NORMAL; };
            struct v2f { float4 pos : SV_POSITION; };
            v2f vert (appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex);
                float3 vn = mul((float3x3)UNITY_MATRIX_IT_MV, v.normal);
                float2 off = normalize(TransformViewToProjection(vn.xy) + 1e-5);
                o.pos.xy += off * _OutlineWidth * o.pos.w; return o; }
            fixed4 frag (v2f i) : SV_Target { return lerp(_OutlineColor, fixed4(1,1,1,1), _Flash); }
            ENDCG
        }
    }
    Fallback "VertexLit"
}
