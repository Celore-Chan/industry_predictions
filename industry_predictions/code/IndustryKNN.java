package exp5;

import java.io.BufferedReader;
import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.URI;
import java.util.*;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

public class IndustryKNN {

    // ================= Mapper =================
    public static class KNNMapper extends Mapper<Object, Text, IntWritable, Text> {

        private List<String> testCodes = new ArrayList<>();
        private List<String> testNames = new ArrayList<>();
        private List<double[]> testFeatures = new ArrayList<>();
        
        private int stFilteredCount = 0;
        private int normalCount = 0;
        private boolean trainHeaderSkipped = false;  // 训练集表头标记

        @Override
        protected void setup(Context context) throws IOException {
            URI[] cacheFiles = context.getCacheFiles();
            if (cacheFiles == null || cacheFiles.length == 0) {
                throw new RuntimeException("未设置测试集缓存文件");
            }
            
            BufferedReader reader = null;
            try {
                String cachePath = cacheFiles[0].getPath();
                System.out.println("缓存文件路径: " + cachePath);
                
                if (cacheFiles[0].getScheme() != null && cacheFiles[0].getScheme().equals("hdfs")) {
                    FileSystem fs = FileSystem.get(context.getConfiguration());
                    Path path = new Path(cacheFiles[0]);
                    reader = new BufferedReader(new InputStreamReader(fs.open(path)));
                } else {
                    reader = new BufferedReader(new FileReader(cachePath));
                }
            } catch (FileNotFoundException e) {
                String fileName = new Path(cacheFiles[0].getPath()).getName();
                reader = new BufferedReader(new FileReader(fileName));
            }
            
            String line;
            int headerSkipped = 0;
            int dataLoaded = 0;
            
            while ((line = reader.readLine()) != null) {
                // ===== 跳过表头 =====
                if (headerSkipped == 0) {
                    headerSkipped = 1;
                    // 判断第一行是否为表头（含字母或中文）
                    if (isHeaderLine(line)) {
                        System.out.println("测试集表头已跳过: " + line.substring(0, Math.min(50, line.length())));
                        continue;
                    }
                }
                
                String[] parts = line.trim().split(",");
                if (parts.length < 29) continue;
                
                testCodes.add(parts[0]);     // ts_code
                testNames.add(parts[1]);     // name
                
                double[] feats = new double[27];
                for (int i = 0; i < 27; i++) {
                    try {
                        feats[i] = Double.parseDouble(parts[i + 2]);
                    } catch (NumberFormatException ex) {
                        feats[i] = 0.0;
                    }
                }
                testFeatures.add(feats);
                dataLoaded++;
            }
            reader.close();
            
            System.out.println("测试集: 表头已跳过, 加载 " + dataLoaded + " 条样本");
        }

        /**
         * 判断是否为表头行（含非数字的字段名）
         */
        private boolean isHeaderLine(String line) {
            if (line == null || line.isEmpty()) return false;
            String lower = line.toLowerCase();
            return lower.contains("ts_code") || 
                   lower.contains("code") || 
                   lower.contains("name") || 
                   lower.contains("industry") ||
                   lower.contains("roe") || 
                   lower.contains("gross_margin") ||
                   !lower.matches(".*\\d.*");  // 不含任何数字
        }

        @Override
        protected void map(Object key, Text value, Context context)
                throws IOException, InterruptedException {
            
            String line = value.toString();
            
            // ===== 跳过训练集第一行表头 =====
            if (!trainHeaderSkipped) {
                trainHeaderSkipped = true;
                if (isHeaderLine(line)) {
                    System.out.println("训练集表头已跳过: " + line.substring(0, Math.min(50, line.length())));
                    return;
                }
            }
            
            String[] parts = line.split(",");
            if (parts.length < 30) return;

            String name = parts[1].trim();
            
            // 过滤 ST 企业
            if (isSTCompany(name)) {
                stFilteredCount++;
                return;
            }
            
            normalCount++;
            String label = parts[2].trim();
            
            double[] trainFeat = new double[27];
            for (int i = 0; i < 27; i++) {
                try {
                    trainFeat[i] = Double.parseDouble(parts[i + 3]);
                } catch (NumberFormatException e) {
                    trainFeat[i] = 0.0;
                }
            }

            for (int i = 0; i < testFeatures.size(); i++) {
                double dist = euclidean(trainFeat, testFeatures.get(i));
                String outValue = testCodes.get(i) + "|" + testNames.get(i) + "|" + dist + "@" + label;
                context.write(new IntWritable(i), new Text(outValue));
            }
        }

        private boolean isSTCompany(String name) {
            if (name == null || name.isEmpty()) return false;
            String upperName = name.toUpperCase().replaceAll("\\s+", "");
            return upperName.contains("*ST") || 
                   upperName.contains("ST") || 
                   upperName.startsWith("SST") ||
                   upperName.contains("S*ST");
        }

        private double euclidean(double[] a, double[] b) {
            double sum = 0.0;
            for (int i = 0; i < a.length; i++) {
                sum += Math.pow(a[i] - b[i], 2);
            }
            return Math.sqrt(sum);
        }

        @Override
        protected void cleanup(Context context) throws IOException, InterruptedException {
            System.out.println("===== Mapper 统计 =====");
            System.out.println("ST企业已过滤: " + stFilteredCount + " 家");
            System.out.println("正常企业参与训练: " + normalCount + " 家");
        }
    }

    // ================= Reducer =================
    public static class KNNReducer extends Reducer<IntWritable, Text, Text, Text> {
        private int k;

        @Override
        protected void setup(Context context) {
            k = context.getConfiguration().getInt("k", 7);
        }

        @Override
        protected void reduce(IntWritable testId, Iterable<Text> values, Context context)
                throws IOException, InterruptedException {
            
            TreeMap<Double, String[]> sorted = new TreeMap<>();
            String tsCode = "unknown";
            String name = "unknown";
            int totalNeighbors = 0;
            
            for (Text val : values) {
                String full = val.toString();
                
                int pipeIdx = full.indexOf('|');
                int pipeIdx2 = full.indexOf('|', pipeIdx + 1);
                
                if (pipeIdx < 0 || pipeIdx2 < 0) continue;
                
                tsCode = full.substring(0, pipeIdx);
                name = full.substring(pipeIdx + 1, pipeIdx2);
                String distAndLabel = full.substring(pipeIdx2 + 1);
                
                String[] parts = distAndLabel.split("@");
                if (parts.length == 2) {
                    try {
                        double dist = Double.parseDouble(parts[0]);
                        String label = parts[1];
                        sorted.put(dist, new String[]{label, tsCode, name});
                        totalNeighbors++;
                    } catch (NumberFormatException ignored) {}
                }
            }

            if (sorted.isEmpty()) return;

            Map<String, Integer> votes = new HashMap<>();
            int cnt = 0;
            for (Map.Entry<Double, String[]> entry : sorted.entrySet()) {
                if (cnt >= k) break;
                String[] info = entry.getValue();
                String label = info[0];
                votes.put(label, votes.getOrDefault(label, 0) + 1);
                cnt++;
            }

            String predictedIndustry = Collections.max(votes.entrySet(),
                    Map.Entry.comparingByValue()).getKey();
            int maxVotes = votes.get(predictedIndustry);
            double confidence = (double) maxVotes / Math.min(k, cnt);

            String firstTsCode = sorted.firstEntry().getValue()[1];
            String firstName = sorted.firstEntry().getValue()[2];

            String outputValue = predictedIndustry + "\t" + 
                                 String.format("%.2f", confidence);
            
            context.write(new Text(firstTsCode + "\t" + firstName), new Text(outputValue));
        }
    }

    // ================= Main =================
    public static void main(String[] args) throws Exception {
    	args = new String[]{
    	        "hdfs://localhost:9000/exp5/input/train_standardized.csv",
    	        "hdfs://localhost:9000/exp5/output",
    	        "hdfs://localhost:9000/exp5/input/test_standardized.csv"
    	    };
    	
        if (args.length < 3) {
            System.err.println("用法: IndustryKNN <训练集路径> <输出路径> <测试集缓存路径> [K值]");
            System.exit(1);
        }

        Configuration conf = new Configuration();
        
        int k = 7;
        if (args.length >= 4) {
            k = Integer.parseInt(args[3]);
        }
        conf.setInt("k", k);
        
        Job job = Job.getInstance(conf, "Industry KNN");
        job.setJarByClass(IndustryKNN.class);

        job.setMapperClass(KNNMapper.class);
        job.setReducerClass(KNNReducer.class);

        job.setMapOutputKeyClass(IntWritable.class);
        job.setMapOutputValueClass(Text.class);
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(Text.class);

        job.addCacheFile(new URI(args[2]));
        FileInputFormat.addInputPath(job, new Path(args[0]));
        
        Path outputPath = new Path(args[1]);
        FileSystem fs = outputPath.getFileSystem(conf);
        if (fs.exists(outputPath)) {
            fs.delete(outputPath, true);
        }
        FileOutputFormat.setOutputPath(job, outputPath);

        System.out.println("================================");
        System.out.println("K值: " + k + " | 过滤ST: 是 | 跳过表头: 是");
        System.out.println("================================");

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}