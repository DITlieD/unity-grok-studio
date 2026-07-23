using System;
using System.IO;
using System.Text;
using UnityEngine;

namespace UnityGrok.AgentDebug
{
    public class AgentLogBridge : MonoBehaviour
    {
        public bool fullExceptionStacks = true;
        public bool includeWarnings = true;
        public bool includeInfo = false;
        public string subFolder = "AgentDebug";
        public string fileName = "runtime-log.ndjson";

        readonly object _gate = new object();
        string _path;
        StackTraceLogType _prevException;

        void OnEnable()
        {
            string dir = Path.Combine(Application.persistentDataPath, subFolder);
            Directory.CreateDirectory(dir);
            _path = Path.Combine(dir, fileName);
            if (fullExceptionStacks)
            {
                _prevException = Application.GetStackTraceLogType(LogType.Exception);
                Application.SetStackTraceLogType(LogType.Exception, StackTraceLogType.Full);
            }
            Application.logMessageReceivedThreaded += OnLogThreaded;
        }

        void OnDisable()
        {
            Application.logMessageReceivedThreaded -= OnLogThreaded;
            if (fullExceptionStacks) Application.SetStackTraceLogType(LogType.Exception, _prevException);
        }

        void OnLogThreaded(string condition, string stackTrace, LogType type)
        {
            if (type == LogType.Warning && !includeWarnings) return;
            if (type == LogType.Log && !includeInfo) return;

            bool withStack = type == LogType.Error || type == LogType.Exception || type == LogType.Assert;
            var sb = new StringBuilder(256);
            sb.Append("{\"ts\":").Append(Q(DateTime.UtcNow.ToString("o")))
              .Append(",\"type\":").Append(Q(type.ToString()))
              .Append(",\"msg\":").Append(Q(condition));
            if (withStack && !string.IsNullOrEmpty(stackTrace)) sb.Append(",\"stack\":").Append(Q(stackTrace));
            sb.Append("}\n");

            lock (_gate)
            {
                File.AppendAllText(_path, sb.ToString());
            }
        }

        static string Q(string s)
        {
            if (s == null) return "\"\"";
            var sb = new StringBuilder(s.Length + 2);
            sb.Append('"');
            foreach (char c in s)
            {
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4"));
                        else sb.Append(c);
                        break;
                }
            }
            sb.Append('"');
            return sb.ToString();
        }
    }
}
