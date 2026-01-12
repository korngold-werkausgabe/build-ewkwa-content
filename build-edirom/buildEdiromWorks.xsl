<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:mei="http://www.music-encoding.org/ns/mei" xmlns:xs="http://www.w3.org/2001/XMLSchema" exclude-result-prefixes="xs mei" version="2.0">
  
  <xsl:output indent="yes"/>
  
  <xsl:param name="annots" select="document('./tmp/annots.xml')" />
  <xsl:param name="property" select="document('../../properties.xml')//property" />
  <xsl:param name="uuid" select="$property[@name='uuids']//uuid" />
  
  <xsl:template match="mei:mei">
    <mei:mei xml:id="{$uuid[@name='editionWork']/text()}">
      <xsl:apply-templates select="@*[name() != 'xml:id'] | node()" />
    </mei:mei>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:fileDesc/mei:titleStmt/mei:title">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:value-of select="$property[@name='workTitle']/text()"/>
    </xsl:copy>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:fileDesc/mei:editionStmt/mei:edition">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:value-of select="$property[@name='editionTitle']/text()"/>
    </xsl:copy>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:workList/mei:work">
    <work xmlns="http://www.music-encoding.org/ns/mei" xml:id="{$uuid[@name='work']/text()}">
      <xsl:apply-templates select="@*[name() != 'xml:id'] | node()" />
    </work>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:workList/mei:work/mei:title">
    <title xml:lang="de"><xsl:value-of select="$property[@name='workTitle']/text()"/></title>
    <title xml:lang="en"><xsl:value-of select="$property[@name='workTitle']/text()"/></title>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:workList/mei:work/mei:notesStmt">
    <notesStmt xmlns="http://www.music-encoding.org/ns/mei">
      <xsl:copy-of select="$annots"/>
    </notesStmt>
  </xsl:template>
    
  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()" />
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>