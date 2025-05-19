using System;
using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;

using System.Text.Json;

class Program
{
    static ConcurrentQueue<string> messageQueue = new ConcurrentQueue<string>(); // 儲存收到的訊息

    static NetworkStream? currentClientStream = null;

    static async Task Main()
    {
        TcpListener server = new TcpListener(IPAddress.Any, 6400);
        server.Start();
        Console.WriteLine("C# TCP Server started...");

        // 印出本機 IP
        string localIP = GetLocalIPAddress();
        Console.WriteLine("Server IP: " + localIP);

        _ = ProcessMessagesAsync(); // 開啟獨立 Task 處理訊息佇列

        while (true)
        {
            TcpClient client = await server.AcceptTcpClientAsync();
            _ = HandleClientAsync(client); // 開新 Task 處理客戶端
        }
    }

    static async Task HandleClientAsync(TcpClient client)
    {
        Console.WriteLine("Client connected.");
        try
        {
            using (NetworkStream stream = client.GetStream())
            {
                currentClientStream = stream;

                byte[] buffer = new byte[1024];

                while (true) // 允許持續接收多筆資料
                {
                    int bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length);
                    if (bytesRead == 0) break; // 連線已關閉

                    string message = Encoding.UTF8.GetString(buffer, 0, bytesRead).Trim();
                    Console.WriteLine("Received from Node.js: " + message);

                    if (message.ToLower() == "exit")
                    {
                        Console.WriteLine("Client requested to close connection.");
                        break; // 結束與此客戶端的溝通
                    }

                    // 將訊息加入佇列
                    messageQueue.Enqueue(message);

                    // 回傳 ACK
                    byte[] response = Encoding.UTF8.GetBytes("ACK: " + message);
                    await stream.WriteAsync(response, 0, response.Length);
                }
            }
        }
        catch (Exception ex)
        {
					try
        	{
						Console.WriteLine("Error in HandleClientAsync:");
            Console.WriteLine("Error: " + ex.Message);
						Console.WriteLine("StackTrace: " + ex.StackTrace);
					}
					catch
					{
							Console.WriteLine("⚠ Exception caught, but unable to display error details.");
					}
        }
        finally
        {
            client.Close();
            currentClientStream = null;
            Console.WriteLine("Client disconnected.");
        }
    }

    static async Task ProcessMessagesAsync()
    {
        while (true)
        {
            //while (messageQueue.TryDequeue(out string message))
            while (messageQueue.TryDequeue(out string? message))
            {
                //await ProcessMessageAsync(message);
                if (message != null)
                {
                    await ProcessMessageAsync(message);
                }
            }
            await Task.Delay(500); // 避免 CPU 過度忙碌
        }
    }

    static async Task ProcessMessageAsync(string message)
    {
				//在switch-case 結構中，使用 {} 包起來讓裡面的變數在作用域中獨立使用, 處理區域變數名稱衝突
        switch (message.ToLower())
        {
            case "station1_call":
                await SendMessageSequenceAsync("station1_agv_ready", 3000);
                await SendMessageSequenceAsync("station1_agv_start", 3000);
                await SendMessageSequenceAsync("station1_agv_begin", 5000);
                await SendMessageSequenceAsync("station2_agv_end", 0);
                break;
            case "station2_call":
                await SendMessageSequenceAsync("station2_agv_ready", 3000);
                await SendMessageSequenceAsync("station2_agv_start", 3000);
                await SendMessageSequenceAsync("station2_agv_begin", 5000);
                await SendMessageSequenceAsync("station3_agv_end", 0);
                break;
            case "station1_loading":
						{
                var data = new StationLoadingData
                {
                    message = 1,
                };
                string jsonData = JsonSerializer.Serialize(data);   // 序列化為 JSON 字串
                string fullMessage = $"station1_loading_ready:{jsonData}";
                Console.WriteLine(fullMessage);
                await SendMessageSequenceAsync(fullMessage, 0);
                break;
						}
            case "station2_loading":
						{
                var data = new StationLoadingData
                {
                    message = 2,
                };
                string jsonData = JsonSerializer.Serialize(data);   // 序列化為 JSON 字串
                string fullMessage = $"station2_loading_ready:{jsonData}";
                Console.WriteLine(fullMessage);
                await SendMessageSequenceAsync(fullMessage, 0);
                break;
						}
            case "station3_loading":
						{
                var data = new StationLoadingData
                {
                    message = 3,
                };
                string jsonData = JsonSerializer.Serialize(data);   // 序列化為 JSON 字串
                string fullMessage = $"station3_loading_ready:{jsonData}";
                Console.WriteLine(fullMessage);
                await SendMessageSequenceAsync(fullMessage, 0);
                break;
						}
            default:
                Console.WriteLine($"Unhandled message: {message}");
                break;
        }
    }

    static string GetLocalIPAddress()
    {
        var host = Dns.GetHostEntry(Dns.GetHostName());
        foreach (var ip in host.AddressList)
        {
            if (ip.AddressFamily == AddressFamily.InterNetwork)
            {
                return ip.ToString();
            }
        }
        return "No IPv4 address found";
    }

    static async Task SendMessageSequenceAsync(string message, int delay)
    {
			Console.WriteLine($"Processing: {message}");
			await Task.Delay(delay);

			try
			{
        if (currentClientStream != null && currentClientStream.CanWrite)
        {
            byte[] data = Encoding.UTF8.GetBytes(message);
            //await currentClientStream.WriteAsync(data, 0, data.Length);
            await currentClientStream!.WriteAsync(data, 0, data.Length);
            Console.WriteLine($"Sent to Node.js: {message}");
        }
        else
        {
            Console.WriteLine("⚠ 無法發送：currentClientStream 無效");
        }
        //Console.WriteLine($"Sent to Node.js: {message}");
			}
    	catch (Exception ex)
    	{
        try
        {
            Console.WriteLine("Error in SendMessageSequenceAsync:");
            Console.WriteLine("Message: " + ex.Message);
            Console.WriteLine("StackTrace: " + ex.StackTrace);
        }
        catch
        {
            Console.WriteLine("⚠ Exception caught, but unable to display error details.");
        }
			}
    }

    public class StationLoadingData
    {
        public int message { get; set; }
    }
}
